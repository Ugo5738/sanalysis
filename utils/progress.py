import json
from datetime import datetime
from typing import Any, Dict, Optional

from asgiref.sync import sync_to_async
from analysis_service.config.logging_config import configure_logger
from django.utils import timezone
from image_condition_analysis.models import (
    AnalysisEvent,
    AnalysisTask,
    WorkflowStatus,
)
from image_condition_analysis.utils.status_notifier import get_status_notifier


def _serialize_for_json(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

logger = configure_logger(__name__)

def _extract_callback_urls(callback_urls_payload: Any) -> list[str]:
    if not isinstance(callback_urls_payload, dict):
        return []
    urls: list[str] = []
    workflow_url = callback_urls_payload.get("workflow_callback_url")
    external_url = callback_urls_payload.get("external_callback_url")
    if workflow_url:
        urls.append(str(workflow_url))
    if external_url:
        urls.append(str(external_url))
    return list(dict.fromkeys(urls))


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
    workflow_record = None

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
    else:
        try:
            defaults = {
                "property_id": getattr(task, "property_id", None),
                "status": status,
                "stage": stage,
                "progress": progress,
                "last_error": (extra or {}).get("error")
                if status_override == "failed"
                else None,
            }
            snapshot_location = (snapshot or {}).get("data_location") if snapshot else None
            if snapshot_location:
                defaults["data_location"] = snapshot_location
            workflow_record, _ = await sync_to_async(
                WorkflowStatus.objects.update_or_create, thread_sensitive=True
            )(
                super_id=super_id,
                context="image_condition_analysis",
                defaults=defaults,
            )
        except Exception as e:
            logger.warning(
                "Failed to upsert WorkflowStatus for super_id=%s: %s", super_id, e
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
        callback_urls_payload = (task.notes or {}).get("callback_urls") if hasattr(task, "notes") else None
        webhook_urls = _extract_callback_urls(callback_urls_payload)
        metadata = {
            "callback_url": task.callback_url,
            "callback_urls": callback_urls_payload,
            "total_images": task.total_images,
            "notes": task.notes or {},
            "property_id": getattr(task, "property_id", None),
        }
        summary = {
            "stage": task.stage,
            "progress": task.progress,
            "status": task.status,
        }
        snapshot_url = await notifier.notify(
            super_id=super_id,
            status=status,
            context="image_condition_analysis",
            data=data,
            summary=summary,
            metadata=metadata,
            webhook_url=task.callback_url,
            webhook_urls=webhook_urls,
            webhook_headers=task.callback_headers,
        )
        if snapshot and snapshot_url:
            snapshot["data_location"] = snapshot_url
        if snapshot_url and (
            not workflow_record or workflow_record.data_location != snapshot_url
        ):
            try:
                if workflow_record:
                    workflow_record.data_location = snapshot_url
                    await sync_to_async(workflow_record.save, thread_sensitive=True)()
                else:
                    await sync_to_async(
                        WorkflowStatus.objects.filter(
                            super_id=super_id, context="image_condition_analysis"
                        ).update,
                        thread_sensitive=True,
                    )(data_location=snapshot_url)
            except Exception as e:
                logger.warning(
                    "Failed to persist data_location for super_id=%s: %s", super_id, e
                )
