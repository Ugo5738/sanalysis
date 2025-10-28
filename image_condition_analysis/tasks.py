import json
from datetime import datetime, timezone
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


def _snapshot_copy(payload: dict) -> dict:
    try:
        return json.loads(json.dumps(payload))
    except (TypeError, ValueError):
        return payload.copy()


@shared_task()
def analyze_images_direct(
    super_id: str,
    image_urls: list,
    notes: Optional[dict] = None,
    callback: Optional[dict] = None,
    property_id: Optional[str] = None,
):
    """Entry point for direct image condition analysis using provided URLs.

    This task is decoupled from any orchestrator and relies solely on inputs.
    """
    logger.info("Starting analyze_images_direct task...")
    async_to_sync(analyze_images_direct_async)(
        super_id, image_urls, notes, callback, property_id
    )
    logger.info("Done analyze_images_direct task...")


async def analyze_images_direct_async(
    super_id: str,
    image_urls: list,
    notes: Optional[dict],
    callback: Optional[dict],
    property_id: Optional[str],
):
    analysis_service = AnalysisService(super_id)
    task_instance = None
    status_report = {
        "super_id": super_id,
        "property_id": property_id,
        "notes": notes or {},
        "image_urls": image_urls,
        "downloads": {},
        "stages": {},
        "final_result": None,
        "errors": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    async def emit(
        stage_name: str,
        msg: str,
        prog: float,
        *,
        status_override: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> None:
        status_report["stages"][stage_name] = {
            "message": msg,
            "progress": prog,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        snapshot_payload = _snapshot_copy(status_report)
        await update_progress(
            super_id,
            stage_name,
            msg,
            prog,
            status_override=status_override,
            extra=extra,
            snapshot=snapshot_payload,
        )
    try:
        # Create or get task record
        task_instance = await analysis_service.get_or_create_task()
        task_instance.total_images = len(image_urls)
        if property_id:
            task_instance.property_id = property_id
        if callback:
            task_instance.callback_url = callback.get("url")
            headers = callback.get("headers") or {}
            if isinstance(headers, dict):
                task_instance.callback_headers = {
                    str(key): str(value) for key, value in headers.items()
                }
        await task_instance.asave()
        # Persist notes payload on the task for traceability
        if notes is not None:
            try:
                task_instance.notes = notes
                await task_instance.asave()
            except Exception:
                # Non-fatal if storing notes fails
                pass

        # Initial progress
        await emit(
            "init",
            "Starting analysis",
            0.0,
            status_override="started",
            extra={"image_count": len(image_urls), "property_id": property_id},
        )

        # Create minimal Property aggregator for this run
        property_instance = Property(
            super_id=super_id,
            property_id=property_id,
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
        status_report["property_record_id"] = property_instance.id
        await emit("download", "Downloading images", 0.0)
        image_ids, failed_downloads = await download_images(
            property_instance,
            lambda stage, msg, prog: emit(
                stage,
                msg,
                prog,
                extra={"property_id": property_id},
            ),
        )
        property_instance.failed_downloads = failed_downloads
        await property_instance.asave()
        status_report["downloads"] = {
            "image_ids": image_ids,
            "failed_downloads": failed_downloads,
        }

        # Process property for condition analysis
        await emit("analysis", "Running analysis", 60.0)
        final_result = await process_property(
            image_ids,
            lambda stage, msg, prog: emit(
                stage,
                msg,
                prog,
                extra={"property_id": property_id},
            ),
            super_id,
        )

        # Mark complete
        task_instance.status = "COMPLETED"
        task_instance.progress = 100.0
        task_instance.stage = "complete"
        await task_instance.asave()
        status_report["final_result"] = final_result
        status_report["completed_at"] = datetime.now(timezone.utc).isoformat()
        await emit(
            "complete",
            "Analysis completed",
            100.0,
            extra={"final_result": final_result, "property_id": property_id},
        )
    except Exception as e:
        logger.error(f"Direct analysis failed: {e}", exc_info=True)
        status_report["errors"].append(
            {
                "message": str(e),
                "stage": task_instance.stage if task_instance else "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        status_report["failed_at"] = datetime.now(timezone.utc).isoformat()
        await emit(
            "error",
            f"Error: {e}",
            0.0,
            status_override="failed",
            extra={"error": str(e), "property_id": property_id},
        )
        if task_instance:
            task_instance.status = "ERROR"
            await task_instance.asave()
