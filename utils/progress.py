import json
from datetime import datetime
from typing import Any, Dict, Optional

from analysis_service.config.logging_config import configure_logger
from django.utils import timezone
from image_condition_analysis.models import AnalysisEvent, AnalysisTask
from image_condition_analysis.utils.status_notifier import get_status_notifier


def _serialize_for_json(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

logger = configure_logger(__name__)


async def update_progress(
    super_id: str,
    stage: str,
    message: str,
    progress: float,
    status_override: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist progress locally and emit an AnalysisEvent.

    This function decouples progress reporting from any external orchestrator.
    It upserts the AnalysisTask for the given super_id and logs a PROGRESS event.
    """
    progress = float(progress)
    progress_data = {"stage": stage, "message": message, "progress": progress}
    task = None
    status = status_override or ("completed" if progress >= 100.0 else "in_progress")

    # Upsert AnalysisTask status/progress
    try:
        try:
            task = await AnalysisTask.objects.aget(super_id=super_id)
        except AnalysisTask.DoesNotExist:
            task = AnalysisTask(
                super_id=super_id,
                status="PENDING",
                progress=0.0,
                stage="",
                stage_progress={},
            )
            await task.asave()

        task.stage = stage or task.stage
        task.progress = progress
        stage_progress = task.stage_progress or {}
        stage_progress[stage] = {
            "message": message,
            "progress": progress,
            "updated_at": timezone.now().isoformat(),
        }
        task.stage_progress = stage_progress
        if status_override == "failed":
            task.status = "ERROR"
        elif progress >= 100.0:
            task.status = "COMPLETED"
        elif status_override == "started":
            task.status = "IN_PROGRESS"
        elif task.status not in ("COMPLETED", "ERROR"):
            task.status = "IN_PROGRESS"
        await task.asave()
    except Exception as e:
        logger.warning(
            f"Failed to update AnalysisTask progress for super_id={super_id}: {e}"
        )

    # Log AnalysisEvent for traceability
    try:
        await AnalysisEvent.objects.acreate(
            super_id=super_id,
            event_type="PROGRESS",
            source="image_condition_service",
            target="local",
            endpoint=None,
            method=None,
            http_status=None,
            error_code=None,
            error_message=None,
            request_payload=progress_data,
            response_payload={},
            response_count=None,
            meta={},
        )
    except Exception as e:
        logger.warning(
            f"Failed to log progress AnalysisEvent for super_id={super_id}: {e}"
        )

    # Broadcast status notification if enabled
    notifier = get_status_notifier()
    if notifier and task:
        data = {
            "stage": stage,
            "message": message,
            "progress": progress,
            "stage_progress": task.stage_progress or {},
            "property_id": task.property_id,
        }
        if snapshot:
            try:
                data["details"] = json.loads(
                    json.dumps(snapshot, default=_serialize_for_json)
                )
            except Exception:
                data["details"] = snapshot
        if extra:
            data["extra"] = extra
        metadata = {
            "callback_url": task.callback_url,
            "total_images": task.total_images,
            "notes": task.notes or {},
            "property_id": getattr(task, "property_id", None),
        }
        summary = {
            "stage": task.stage,
            "progress": task.progress,
            "status": task.status,
        }
        await notifier.notify(
            super_id=super_id,
            status=status,
            context="image_condition_analysis",
            data=data,
            summary=summary,
            metadata=metadata,
            webhook_url=task.callback_url,
            webhook_headers=task.callback_headers,
        )
