import json
from typing import Dict, List

from analysis_service.config.logging_config import configure_logger
from channels.layers import get_channel_layer
from image_condition_analysis.models import AnalysisTask, Property
from utils.openai_analysis import analyze_single_floorplan_image

logger = configure_logger(__name__)


class AnalysisService:
    def __init__(self, super_id: str):
        self.super_id = super_id
        self.channel_layer = get_channel_layer()

    async def get_or_create_task(self) -> AnalysisTask:
        try:
            task_instance = await AnalysisTask.objects.aget(super_id=self.super_id)
            logger.info(f"Task instance retrieved: {task_instance}")
            return task_instance
        except AnalysisTask.DoesNotExist:
            logger.info("AnalysisTask does not exist, creating a new one...")
            task_instance = AnalysisTask(
                super_id=self.super_id,
                status="PENDING",
            )
            await task_instance.asave()
            logger.info(f"New AnalysisTask created: {task_instance}")
            return task_instance

    async def analyze_floorplans(self, floorplan_urls: List[str]) -> List[Dict]:
        results = []
        for url in floorplan_urls:
            response = analyze_single_floorplan_image(url)

            # First, check if the analysis function returned a hard error.
            if "error" in response:
                results.append({"url": url, "error": response["error"]})
                continue  # Skip to the next URL

            # Get the response content from the OpenAI call.
            result_str = response.get("response_content")

            # **FIX:** Check if the result content is a valid string before parsing.
            # This prevents the "the JSON object must be str, bytes or bytearray, not NoneType" error.
            if result_str:
                try:
                    parsed_result = json.loads(result_str)
                    results.append({"url": url, "analysis": parsed_result})
                except json.JSONDecodeError:
                    results.append(
                        {"url": url, "error": "Invalid JSON returned by OpenAI"}
                    )
            else:
                # Handle cases where the response content is None or empty.
                results.append(
                    {"url": url, "error": "Empty content returned from analysis"}
                )
        return results
