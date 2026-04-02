from __future__ import annotations

from redis import Redis
from rq import Queue

from app.config import get_settings


def get_queue() -> Queue:
    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    return Queue(settings.rq_queue_name, connection=connection)


def enqueue_ingestion(
    document_id: str,
    gemini_api_key: str | None = None,
) -> str:
    queue = get_queue()
    job = queue.enqueue(
        "worker.jobs.process_document_ingestion",
        document_id,
        gemini_api_key,
        job_timeout=60 * 20,
    )
    return job.id


def enqueue_drive_import(
    workspace_id: str,
    folder_id: str,
    gemini_api_key: str | None = None,
) -> str:
    queue = get_queue()
    job = queue.enqueue(
        "worker.jobs.import_from_drive",
        workspace_id,
        folder_id,
        gemini_api_key,
        job_timeout=60 * 10,
    )
    return job.id
