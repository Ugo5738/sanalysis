from analysis_service.config.logging_config import configure_logger
from image_condition_analysis.models import AnalysisEvent, AnalysisTask

logger = configure_logger(__name__)


async def update_progress(
    super_id: str,
    stage: str,
    message: str,
    progress: float,
) -> None:
    """Persist progress locally and emit an AnalysisEvent.

    This function decouples progress reporting from any external orchestrator.
    It upserts the AnalysisTask for the given super_id and logs a PROGRESS event.
    """
    progress = float(progress)
    progress_data = {"stage": stage, "message": message, "progress": progress}

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
        stage_progress[stage] = {"message": message, "progress": progress}
        task.stage_progress = stage_progress
        if progress >= 100.0 and task.status != "COMPLETED":
            task.status = "COMPLETED"
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
