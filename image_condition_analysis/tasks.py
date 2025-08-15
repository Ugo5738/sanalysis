from typing import Optional

from analysis_service.config.logging_config import configure_logger
from asgiref.sync import async_to_sync, sync_to_async
from celery import shared_task
from image_condition_analysis.models import Property
from services.analysis_service import AnalysisService
from utils.image_processing import download_images
from utils.progress import update_progress
from utils.property_analysis import process_property

logger = configure_logger(__name__)


@shared_task()
def analyze_images_direct(
    super_id: str,
    image_urls: list,
    notes: Optional[dict] = None,
):
    """Entry point for direct image condition analysis using provided URLs.

    This task is decoupled from any orchestrator and relies solely on inputs.
    """
    logger.info("Starting analyze_images_direct task...")
    async_to_sync(analyze_images_direct_async)(super_id, image_urls, notes)
    logger.info("Done analyze_images_direct task...")


async def analyze_images_direct_async(
    super_id: str, image_urls: list, notes: Optional[dict]
):
    analysis_service = AnalysisService(super_id)
    task_instance = None
    try:
        # Create or get task record
        task_instance = await analysis_service.get_or_create_task()
        # Persist notes payload on the task for traceability
        if notes is not None:
            try:
                task_instance.notes = notes
                await task_instance.asave()
            except Exception:
                # Non-fatal if storing notes fails
                pass

        # Initial progress
        await update_progress(super_id, "init", "Starting analysis", 0.0)

        # Create minimal Property aggregator for this run
        property_instance = Property(
            super_id=super_id,
            image_urls=image_urls or [],
        )
        # Persist early so FK relationships work and IDs are assigned
        await property_instance.asave()

        # Optionally map supported fields from notes
        if notes:
            try:
                if "bedrooms" in notes and notes.get("bedrooms") is not None:
                    try:
                        property_instance.bedrooms = int(notes.get("bedrooms"))
                    except (TypeError, ValueError):
                        pass
                if "floorplan_urls" in notes and isinstance(
                    notes.get("floorplan_urls"), list
                ):
                    property_instance.floorplan_urls = notes.get("floorplan_urls")
                await property_instance.asave()
            except Exception:
                # Non-fatal if mapping fails
                pass

        # Download images
        await update_progress(super_id, "download", "Downloading images", 0.0)
        image_ids, failed_downloads = await download_images(
            property_instance,
            lambda stage, msg, prog: update_progress(super_id, stage, msg, prog),
        )
        property_instance.failed_downloads = failed_downloads
        await property_instance.asave()

        # Process property for condition analysis
        await update_progress(super_id, "analysis", "Running analysis", 60.0)
        await process_property(
            image_ids,
            lambda stage, msg, prog: update_progress(super_id, stage, msg, prog),
            super_id,
        )

        # Mark complete
        task_instance.status = "COMPLETED"
        task_instance.progress = 100.0
        task_instance.stage = "complete"
        await task_instance.asave()
        await update_progress(super_id, "complete", "Analysis completed", 100.0)
    except Exception as e:
        logger.error(f"Direct analysis failed: {e}", exc_info=True)
        await update_progress(super_id, "error", f"Error: {e}", 0.0)
        if task_instance:
            task_instance.status = "ERROR"
            await task_instance.asave()
