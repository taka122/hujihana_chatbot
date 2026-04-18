from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete

from app.db import SessionLocal
from app.models import Chunk, Document, DocumentStatus, IngestionRun
from app.services.embed import EmbeddingService, EmbeddingError
from app.services.ingest import IngestionError, UnsupportedDocumentError, build_chunks, parse_document, import_from_drive_job
from app.services.storage import StorageService
from app.services.drive_service import DriveService
from app.config import get_settings
import json

logger = logging.getLogger(__name__)


def process_document_ingestion(
    document_id: str,
    gemini_api_key: str | None = None,
) -> None:
    db = SessionLocal()
    run: IngestionRun | None = None
    parse_result = None

    try:
        doc_uuid = uuid.UUID(document_id)
        document = db.get(Document, doc_uuid)
        if not document:
            logger.error("Document not found for ingestion: %s", document_id)
            return

        run = IngestionRun(
            document_id=document.id,
            started_at=datetime.now(timezone.utc),
            extracted_pages=0,
            failed_pages_count=0,
            failed_pages=[],
            ocr_used_pages=[],
            chunk_count=0,
            log={"stage": "started"},
        )
        db.add(run)
        db.flush()

        storage = StorageService()
        if document.storage_key.startswith("drive://"):
            # Google Driveからダウンロード
            settings = get_settings()
            sa_path = settings.google_drive_service_account_path
            if not sa_path:
                raise IngestionError("Google Drive service account path is not configured")
            try:
                with open(sa_path, "r", encoding="utf-8") as f:
                    sa_info = json.load(f)
            except OSError as exc:
                raise IngestionError(f"Google Drive service account could not be read: {exc}") from exc
            drive = DriveService(sa_info)
            file_id = document.storage_key.replace("drive://", "")
            raw_bytes = drive.download_file_to_memory(file_id)
        else:
            # 通常のS3(Minio)からダウンロード
            raw_bytes = storage.download_bytes(document.storage_key)

        parse_result = parse_document(
            document.file_name,
            document.mime_type,
            raw_bytes,
            gemini_api_key_override=gemini_api_key,
        )
        chunk_payloads = build_chunks(parse_result.blocks)
        if not chunk_payloads:
            raise IngestionError("No chunks generated from extracted text")

        embedder = EmbeddingService(gemini_api_key=gemini_api_key)
        vectors = embedder.embed_texts([item.text for item in chunk_payloads])

        if len(vectors) != len(chunk_payloads):
            raise IngestionError("Embedding count mismatch")

        db.execute(delete(Chunk).where(Chunk.document_id == document.id))

        for payload, vector in zip(chunk_payloads, vectors):
            db.add(
                Chunk(
                    workspace_id=document.workspace_id,
                    document_id=document.id,
                    chunk_index=payload.chunk_index,
                    text=payload.text,
                    page_start=payload.page_start,
                    page_end=payload.page_end,
                    section_title=payload.section_title,
                    snippet=payload.snippet,
                    embedding=vector,
                )
            )

        tags = sorted(set((document.tags or []) + parse_result.tags))
        document.tags = tags
        document.page_count = parse_result.page_count
        document.fail_reason = None
        document.status = DocumentStatus.ready

        run.extracted_pages = parse_result.extracted_pages
        run.failed_pages = parse_result.failed_pages
        run.failed_pages_count = len(parse_result.failed_pages)
        run.ocr_used_pages = parse_result.ocr_used_pages
        run.chunk_count = len(chunk_payloads)
        run.finished_at = datetime.now(timezone.utc)
        run.log = {
            "stage": "completed",
            "message": "ingestion finished",
            "chunk_count": len(chunk_payloads),
            "tags": tags,
        }

        db.add(document)
        db.add(run)
        db.commit()
        logger.info("Ingestion succeeded: document=%s chunks=%s", document.id, len(chunk_payloads))

    except UnsupportedDocumentError as exc:
        _mark_failed(
            db,
            document_id,
            run,
            reason=str(exc),
            tags=exc.tags,
            failed_pages=parse_result.failed_pages if parse_result else [],
            extracted_pages=parse_result.extracted_pages if parse_result else 0,
            ocr_used_pages=parse_result.ocr_used_pages if parse_result else [],
        )
    except EmbeddingError as exc:
        _mark_failed(
            db,
            document_id,
            run,
            reason=f"embedding_error: {exc}",
            tags=parse_result.tags if parse_result else [],
            failed_pages=parse_result.failed_pages if parse_result else [],
            extracted_pages=parse_result.extracted_pages if parse_result else 0,
            ocr_used_pages=parse_result.ocr_used_pages if parse_result else [],
        )
    except IngestionError as exc:
        _mark_failed(
            db,
            document_id,
            run,
            reason=str(exc),
            tags=parse_result.tags if parse_result else [],
            failed_pages=parse_result.failed_pages if parse_result else [],
            extracted_pages=parse_result.extracted_pages if parse_result else 0,
            ocr_used_pages=parse_result.ocr_used_pages if parse_result else [],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected ingestion failure: %s", document_id)
        _mark_failed(
            db,
            document_id,
            run,
            reason=f"unexpected_error: {exc}",
            tags=parse_result.tags if parse_result else [],
            failed_pages=parse_result.failed_pages if parse_result else [],
            extracted_pages=parse_result.extracted_pages if parse_result else 0,
            ocr_used_pages=parse_result.ocr_used_pages if parse_result else [],
        )
    finally:
        db.close()


def _mark_failed(
    db,
    document_id: str,
    run: IngestionRun | None,
    reason: str,
    tags: list[str],
    failed_pages: list[dict],
    extracted_pages: int,
    ocr_used_pages: list[int],
) -> None:
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        logger.error("Invalid document UUID in failure handler: %s", document_id)
        return

    document = db.get(Document, doc_uuid)
    if document:
        document.status = DocumentStatus.failed
        document.fail_reason = reason
        document.tags = sorted(set((document.tags or []) + tags))
        db.add(document)

    if run:
        run.finished_at = datetime.now(timezone.utc)
        run.extracted_pages = extracted_pages
        run.failed_pages = failed_pages
        run.failed_pages_count = len(failed_pages)
        run.ocr_used_pages = ocr_used_pages
        run.log = {"stage": "failed", "reason": reason, "tags": tags}
        db.add(run)

    db.commit()
    logger.error("Ingestion failed: document=%s reason=%s", document_id, reason)

def import_from_drive(
    workspace_id: str,
    folder_id: str,
    gemini_api_key: str | None = None,
) -> None:
    """Google Driveフォルダのインポートを実行するトップレベルジョブ"""
    logger.info("Worker: import_from_drive job started. wid=%r, fid=%r", workspace_id, folder_id)
    import_from_drive_job(workspace_id, folder_id, gemini_api_key=gemini_api_key)
