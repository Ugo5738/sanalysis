import base64
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from asgiref.sync import sync_to_async

from analysis_service.config.base_config import openai_client as client
from analysis_service.config.logging_config import configure_logger
from utils.prompts import rolf_prompt

logger = configure_logger(__name__)


def encode_image(image_file) -> str:
    """Encode an image file to base64 string."""
    with image_file.open("rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def log_openai_cost(
    *,
    super_id: Optional[str],
    stage: str,
    model: str,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    prompt_cost: Optional[float],
    completion_cost: Optional[float],
    path: str = "logs/openai_costs.log",
) -> None:
    """
    Append a JSON line with cost details for a given super_id/stage.
    Creates the log directory if it does not exist.
    """
    try:
        log_dir = os.path.dirname(path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "super_id": super_id,
            "stage": stage,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "prompt_cost_usd": prompt_cost,
            "completion_cost_usd": completion_cost,
            "total_cost_usd": (prompt_cost or 0.0) + (completion_cost or 0.0),
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:  # defensive logging only
        logger.warning(f"Failed to log OpenAI cost: {e}")


def process_image_input(target_image: str) -> Optional[Dict[str, Any]]:
    """
    Process and validate different types of image inputs (base64, file path, URL).
    Returns a dictionary suitable for the OpenAI API image_url format.
    """
    try:
        if not isinstance(target_image, str):
            raise ValueError(
                "Target image must be a string path, URL, or base64 data URI."
            )

        if target_image.startswith("data:image/jpeg;base64,"):
            image_url = target_image
        elif os.path.isfile(target_image):
            base64_image = encode_image(target_image)
            image_url = f"data:image/jpeg;base64,{base64_image}"
        elif target_image.startswith("http"):
            image_url = target_image
        else:
            raise ValueError("Unrecognized image format")

        return {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}}
    except Exception as e:
        logger.error(f"Error processing image input: {str(e)}")
        return None


def analyze_image(
    text_prompt: str,
    target_image: str,
    model: str = "gpt-4o",
    sample_images_dict: Optional[Dict[str, str]] = None,
    response_format: Optional[Dict[str, Any]] = {"type": "json_object"},
) -> Dict[str, Any]:
    """
    Generic image analysis function that can be used for different types of image analysis.

    Args:
        text_prompt: The instruction prompt for the analysis
        target_image: The image to analyze (base64 string, file path, or URL)
        model: The OpenAI model to use
        sample_images_dict: Optional dictionary of sample images for comparison
        response_format: Optional response format specification

    Returns:
        Dictionary containing analysis results and usage statistics
    """
    try:
        # Initialize messages with the text prompt
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": text_prompt,
                    }
                ],
            }
        ]

        # Add sample images if provided
        if sample_images_dict:
            for condition, image_base64 in sample_images_dict.items():
                image_content = process_image_input(image_base64)
                if image_content:
                    messages[0]["content"].append(image_content)

        # Process target image
        target_image_content = process_image_input(target_image)
        if not target_image_content:
            raise ValueError("Failed to process target image")

        messages[0]["content"].append(target_image_content)

        # Make API call
        response = client.chat.completions.create(
            model=model, messages=messages, response_format=response_format
        )

        # Calculate costs based on model
        prompt_cost_per_token = 5 if model == "gpt-4o" else 2.5
        completion_cost_per_token = 15 if model == "gpt-4o" else 1.25

        return {
            "response_content": response.choices[0].message.content,
            "prompt_tokens": response.usage.prompt_tokens,
            "prompt_tokens_cost": (response.usage.prompt_tokens * prompt_cost_per_token)
            / 1000000,
            "completion_tokens": response.usage.completion_tokens,
            "completion_tokens_cost": (
                response.usage.completion_tokens * completion_cost_per_token
            )
            / 1000000,
        }

    except Exception as e:
        logger.error(f"Error in analyze_image: {str(e)}")
        return {"error": str(e)}


def analyze_single_image(
    text_prompt: str,
    target_image: str,
    sample_images_dict: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Specific implementation for general image analysis."""
    return analyze_image(
        text_prompt=text_prompt,
        target_image=target_image,
        sample_images_dict=sample_images_dict,
    )


def analyze_single_floorplan_image(target_image: str) -> Dict[str, Any]:
    """Specific implementation for floorplan analysis."""
    floorplan_prompt = """You are a UK residential floorplan expert. You specialize in reviewing floorplan images and extracting 
            specific details.

            Only mark 'background_image_in_blueprint' as true if:
            1. There is a watermark, logo, or any background image (branding, watermark graphics, patterns) 
            **overlaid on top of or behind the actual building blueprint lines**. 
            - This means it appears visually integrated or layered with the walls, rooms, or other line 
                drawings of the plan itself.
            2. A logo or decorative element is inside or behind the building footprint, so that it overlaps 
            with or sits underneath the drawn lines.

            If the text, logo, or branding is **only** in the corner, margin, or outside the drawn blueprint lines 
            (e.g., disclaimers, brand text placed below or above the plan), and there is **no** overlapping with 
            the blueprint lines, then 'background_image_in_blueprint' must be false.

            ### Examples ###
            1) A faint brand name spread across the blueprint lines, or a logo behind the rooms, or a tinted 
            decorative background behind the lines: background_image_in_blueprint = true.
            2) If a disclaimer is clearly below or off to the side of the drawing, not overlapping or behind the 
            blueprint lines: background_image_in_blueprint = false.
            3) If the background is plain white (or transparent) without any decorative patterns behind the drawn 
            lines: background_image_in_blueprint = false.

            ### Questions ###
            For each floorplan image, please provide:

            1. color: Is the floorplan black & white or colour? (possible values: 'black & white' or 'colour')
            2. dimension_type: Is the plan 2D or 3D? (possible values: '2D' or '3D')
            3. drawing_type: Is it computer-generated or hand-drawn? (possible values: 'Computer Generated' or 'Hand-drawn')
            4. background_image_in_blueprint: (true or false) - only true if there's a logo/image/text/pattern overlapping or behind 
            the blueprint lines, per the criteria above. Also tell me what area in the floor plan image you found this, if you select true
            5. number_buildings: How many separate buildings are there (e.g. main house, annex, outbuildings, garage)?
            6. number_floors: How many floors are shown?
            7. bay_windows: Are there bay windows (true or false)?
            8. curved_walls_windows: Are there curved walls or windows (true or false)?
            9. garden: Is there a garden shown (true or false)?
            10. total_square_area: What is the total square area shown? Please provide both meters and feet, if available, 
                in the format 'xx sqm / yy sqft'. Otherwise, use 'N/A'.
            11. main_building_square_area: What is the main building/house square area? Provide both meters and feet, 
                or 'N/A' if unavailable.
            12. compass_direction: Does the image show a compass? If yes, specify the direction (N, S, E, W, NW, NE, SW, SE); 
                otherwise use 'N/A'.
            13. key_observations: Provide any key observations in no more than 50 words.

            ### Output Format ###
            Return exactly one JSON object with these keys:
            {
                "color": "black & white" or "colour",
                "dimension_type": "2D" or "3D",
                "drawing_type": "Computer Generated" or "Hand-drawn",
                "background_image_in_blueprint": true or false,
                "number_buildings": <integer>,
                "number_floors": <integer>,
                "bay_windows": true or false,
                "curved_walls_windows": true or false,
                "garden": true or false,
                "total_square_area": "<xx sqm / yy sqft>" or "N/A",
                "main_building_square_area": "<xx sqm / yy sqft>" or "N/A",
                "compass_direction": "N" or "S" or "E" or "W" or "NW" or "NE" or "SW" or "SE" or "N/A",
                "key_observations": "Your short comment (max 50 words)"
            }

            Do not provide any additional commentary outside of the JSON. Your entire response should be a valid 
            JSON object matching the above format and key names exactly.
        """

    return analyze_image(
        text_prompt=floorplan_prompt, target_image=target_image, model="gpt-4o"
    )


# update the JSON file
async def update_prompt_json_file(spaces, classifications):
    for classification in classifications["images"]:
        category = classification["category"]
        details = classification["details"]

        if category == "internal":
            room_type = details.get("room_type")
            if room_type and room_type not in sum(spaces.values(), []):
                spaces["living_space"].append(room_type)
            if "others" in details:
                other_type = details["others"]
                if other_type not in spaces["others"]:
                    spaces["others"].append(other_type)

        elif category == "external":
            exterior_type = details.get("exterior_type")
            if exterior_type and exterior_type not in sum(spaces.values(), []):
                spaces["front_garden_space"].append(exterior_type)
            if "others" in details:
                other_type = details["others"]
                if other_type not in spaces["others"]:
                    spaces["others"].append(other_type)

        elif category == "floor plan":
            floor_type = details.get("floor_type")
            if floor_type and floor_type not in spaces["others"]:
                spaces["others"].append(floor_type)

        elif category == "others":
            other_type = details["others"]
            if other_type not in spaces["others"]:
                spaces["others"].append(other_type)

    # Remove duplicates by converting lists to sets and back to lists
    for key in spaces:
        spaces[key] = list(set(spaces[key]))
    # Write the updated JSON back to the file
    with open("utils/data.json", "w") as file:
        json.dump(spaces, file, indent=4)


def get_openai_chat_response(instruction, message, prompt_format):
    start_time = time.time()

    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": message},
    ]

    structured_response = client.chat.completions.create(
        model="gpt-4o-mini",  # "chatgpt-4o-latest",
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "doc_response",
                "strict": True,
                "schema": prompt_format,
            },
        },
    )

    response = json.loads(structured_response.choices[0].message.content)
    total = time.time() - start_time
    logger.info(f"Chat Response Time: {total}")

    return response


class OpenAIService:
    @staticmethod
    async def generate_reviewed_description(
        description: str, features: List[str]
    ) -> Optional[str]:
        try:
            instruction = (
                "Please improve and summarize the following property description "
                "and key features, and produce a reviewed description "
                "suitable for property buyers."
            )
            message = f"Description: {description}\nFeatures: {features}"

            prompt_format = {
                "type": "object",
                "properties": {
                    "reviewed_description": {"type": "string"},
                },
                "required": ["reviewed_description"],
                "additionalProperties": False,
            }

            reviewed_data = await sync_to_async(get_openai_chat_response)(
                instruction, message, prompt_format
            )

            return reviewed_data.get("reviewed_description") if reviewed_data else None

        except Exception as e:
            logger.error(f"Failed to generate reviewed description: {e}")
            return None

    @staticmethod
    async def analyze_description_sentiment(description: str) -> Dict[str, Any]:
        try:
            instruction = (
                "Analyze the sentiment and tone of the following property description. "
                "Consider aspects like professionalism, enthusiasm, honesty, and marketing language. "
                "Provide detailed feedback about the description's effectiveness."
            )

            prompt_format = {
                "type": "object",
                "properties": {
                    "overall_sentiment": {
                        "type": "string",
                        "enum": ["positive", "negative", "neutral", "mixed"],
                    },
                    "sentiment_score": {
                        "type": "number",
                        "description": "Score from -1 (very negative) to 1 (very positive)",
                    },
                    "tone_analysis": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "professionalism": {
                                "type": "number",
                                "description": "Score between 0 to 10",
                            },
                            "enthusiasm": {
                                "type": "number",
                                "description": "Score between 0 to 10",
                            },
                            "objectivity": {
                                "type": "number",
                                "description": "Score between 0 to 10",
                            },
                        },
                        "required": ["professionalism", "enthusiasm", "objectivity"],
                    },
                    "key_phrases": {"type": "array", "items": {"type": "string"}},
                    "marketing_effectiveness": {
                        "type": "string",
                        "description": "Analysis of marketing effectiveness",
                    },
                    "improvement_suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "overall_sentiment",
                    "sentiment_score",
                    "tone_analysis",
                    "key_phrases",
                    "marketing_effectiveness",
                    "improvement_suggestions",
                ],
                "additionalProperties": False,
            }
            sentiment_data = await sync_to_async(get_openai_chat_response)(
                instruction, description, prompt_format
            )

            if not sentiment_data:
                raise ValueError("No sentiment analysis data received")

            return sentiment_data

        except Exception as e:
            logger.error(f"Failed to analyze description sentiment: {e}")
            return {
                "overall_sentiment": "error",
                "sentiment_score": 0,
                "tone_analysis": {
                    "professionalism": 0,
                    "enthusiasm": 0,
                    "objectivity": 0,
                },
                "key_phrases": [],
                "marketing_effectiveness": f"Analysis failed: {str(e)}",
                "improvement_suggestions": [],
            }

    @staticmethod
    async def analyze_description(description: str) -> dict[str, Any]:
        """
        NEW: Analyzes the property description using the Rolf prompt to extract
        condition words, rating, and label.
        Returns a JSON/dict with the extracted words and condition rating & label.
        """
        try:
            prompt_format = {
                "type": "object",
                "properties": {
                    "rating": {"type": "string"},
                    "label": {"type": "string"},
                },
                "required": ["rating", "label"],
                "additionalProperties": False,
            }

            description_analysis = await sync_to_async(get_openai_chat_response)(
                rolf_prompt, description, prompt_format
            )

            if not description_analysis:
                raise ValueError("No description analysis data received")

            return description_analysis

        except Exception as e:
            logger.error(f"Failed to analyze description: {e}", exc_info=True)
            # Either raise or return an error structure
            return {
                "error": str(e),
                "message": "Failed to analyze description via rolf prompt.",
            }
