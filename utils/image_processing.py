import asyncio
import base64
import io

import aiohttp
import clip
import cv2
import numpy as np
import pandas as pd
import torch
from analysis_service.config.logging_config import configure_logger
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from django.utils import timezone
from image_condition_analysis.models import PropertyImage
from PIL import Image

logger = configure_logger(__name__)


# Initialize CLIP model and preprocessing
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)


async def compute_image_embedding(image_content):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, sync_compute_embedding, image_content)


def sync_compute_embedding(image_content):
    image = Image.open(io.BytesIO(image_content)).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = model.encode_image(image_input)
    embedding = embedding.cpu().numpy().flatten()
    return embedding


def compute_embedding(image_path):
    image = Image.open(image_path).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = model.encode_image(image_input)
    embedding = embedding.cpu().numpy().flatten()
    return embedding


async def download_with_requests(image_url):
    """Download an image from a URL using aiohttp."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(image_url, timeout=30) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.warning(
                        f"Failed to download {image_url}, status: {response.status}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error during download of {image_url}: {e}")
            return None


async def download_images(
    property_instance, update_progress, max_retries=3, retry_delay=1, use_selenium=False
):
    image_ids = []
    failed_downloads = []
    total_images = max(len(property_instance.image_urls), 1)

    for idx, image_url in enumerate(property_instance.image_urls):
        downloaded = False
        last_error = None
        for attempt in range(max_retries):
            try:
                img_content = await download_with_requests(image_url)
                if img_content:
                    # Generate a filename
                    file_name = f"property_{property_instance.id}_image_{idx}.jpg"

                    property_image = await PropertyImage.objects.acreate(
                        property=property_instance,
                        original_url=image_url,
                        created_at=timezone.now(),
                    )

                    # Save the image content
                    await sync_to_async(property_image.image.save)(
                        file_name, ContentFile(img_content), save=False
                    )

                    # Compute and store embedding and save the PropertyImage instance
                    embedding = await compute_image_embedding(img_content)
                    property_image.embedding = embedding.tolist()
                    await property_image.asave()

                    logger.info(
                        f"PropertyImage object created with ID: {property_image.id}"
                    )
                    image_ids.append(property_image.id)

                    # Update progress using completed count
                    completed = len(image_ids)
                    progress_percent = (completed / total_images) * 100
                    await update_progress(
                        "download",
                        f"Downloaded image {completed}/{total_images}",
                        progress_percent,
                    )
                    downloaded = True
                    break  # Successful download, move to the next image
                else:
                    last_error = "Empty response body"
            except Exception as e:
                logger.info(f"Error downloading image {idx}: {str(e)}")
                last_error = str(e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
        if not downloaded:
            failed_downloads.append(
                (idx, image_url, last_error or "Failed to download after retries")
            )

    if failed_downloads:
        logger.warning(
            f"Finished processing images with {len(failed_downloads)} failed downloads."
        )
    else:
        logger.info("Finished processing all images successfully.")

    return image_ids, failed_downloads


def resize_with_aspect_ratio(image, target_size):
    img = Image.open(image)
    img = img.convert("RGB")
    img_array = np.array(img)
    h, w = img_array.shape[:2]
    scale = min(target_size[0] / h, target_size[1] / w)
    new_h, new_w = int(h * scale), int(w * scale)
    resized_image = cv2.resize(img_array, (new_w, new_h))

    top = (target_size[0] - new_h) // 2
    bottom = target_size[0] - new_h - top
    left = (target_size[1] - new_w) // 2
    right = target_size[1] - new_w - left

    color = [0, 0, 0]  # black
    padded_image = cv2.copyMakeBorder(
        resized_image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
    )
    return Image.fromarray(padded_image)


async def merge_images(image_objects, condition=None):
    target_size = (256, 256)
    resized_images = [
        resize_with_aspect_ratio(img.image, target_size) for img in image_objects
    ]
    num_images = len(resized_images)

    if num_images == 1:
        merged_image = np.array(resized_images[0])
    elif num_images == 2:
        merged_image = np.zeros((256, 512, 3), dtype=np.uint8)
        merged_image[:, :256] = np.array(resized_images[0])
        merged_image[:, 256:] = np.array(resized_images[1])
        cv2.line(merged_image, (256, 0), (256, 256), (0, 0, 255), 2)
    else:
        merged_image = np.zeros((512, 512, 3), dtype=np.uint8)
        positions = [(0, 0), (0, 256), (256, 0), (256, 256)]
        for i, image in enumerate(resized_images[:4]):
            y, x = positions[i]
            merged_image[y : y + 256, x : x + 256] = np.array(image)[
                :, :, :3
            ]  # Ensure we only take RGB channels
        cv2.line(merged_image, (256, 0), (256, 512), (0, 0, 255), 2)
        cv2.line(merged_image, (0, 256), (512, 256), (0, 0, 255), 2)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    font_color = (255, 255, 255)
    thickness = 2

    label_positions = [(10, 30), (266, 30), (10, 286), (266, 286)]

    for i in range(min(num_images, 4)):
        cv2.putText(
            merged_image,
            str(i + 1),
            label_positions[i],
            font,
            font_scale,
            font_color,
            thickness,
            cv2.LINE_AA,
        )

    if condition:
        condition = condition.upper()
        text_size = cv2.getTextSize(condition, font, font_scale, thickness)[0]
        text_x = (merged_image.shape[1] - text_size[0]) // 2
        text_y = merged_image.shape[0] // 2
        cv2.putText(
            merged_image,
            condition,
            (text_x, text_y),
            font,
            font_scale,
            (0, 255, 0),
            thickness,
            cv2.LINE_AA,
        )

    # Convert the merged image to base64
    img_byte_arr = io.BytesIO()
    Image.fromarray(merged_image).save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


def get_base64_image(image):
    base64_encoded = base64.b64encode(image).decode("utf-8")
    # return f"data:image/png;base64,{base64_encoded}"
    return f"data:image/jpeg;base64,{base64_encoded}"


async def group_images_by_category(image_ids, categories):
    grouped_images = {
        "internal": {},
        "external": {},
        "floor plan": {},
    }
    for image_id, category_info in zip(image_ids, categories):
        category = category_info.get("category", "").lower()
        details = category_info.get("details", {})

        if category == "internal":
            room_type = details.get("room_type", "unknown").lower()
            if room_type != "unknown":
                grouped_images["internal"].setdefault(room_type, []).append(image_id)
        elif category == "external":
            exterior_type = details.get("exterior_type", "unknown").lower()
            if exterior_type != "unknown":
                grouped_images["external"].setdefault(exterior_type, []).append(
                    image_id
                )
        elif category == "floor plan":
            floor_type = details.get("floor_type", "unknown").lower()
            if floor_type != "unknown":
                grouped_images["floor plan"].setdefault(floor_type, []).append(image_id)

    # Remove empty categories
    return {k: v for k, v in grouped_images.items() if v}
