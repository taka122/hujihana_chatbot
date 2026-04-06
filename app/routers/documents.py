from __future__ import annotations

import json
import logging
import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Chunk, Document, DocumentStatus, IngestionRun, Workspace
from app.schemas import (
    ChunkResponse,
    DocumentResponse,
    DriveImportRequest,
    DriveImportResponse,
    IngestionReportResponse,
    PresignedUrlResponse,
    UploadResponse,
)
from app.services.drive_service import DriveService, extract_drive_folder_id, filter_video_files
from app.services.ingest import process_document_ingestion
from app.services.storage import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{wid}", tags=["documents"])


@router.get("/docs", response_model=list[DocumentResponse])
def list_documents(wid: uuid.UUID, db: Session = Depends(get_db)) -> list[Document]:
    _ensure_workspace(db, wid)
    stmt: Select[tuple[Document]] = (
        select(Document)
        .where(Document.workspace_id == wid)
        .order_by(desc(Document.created_at))
    )
    return list(db.scalars(stmt).all())


@router.post("/docs/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    wid: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    _ensure_workspace(db, wid)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_name = file.filename or f"document-{uuid.uuid4()}"
    mime_type = file.content_type or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    doc_id = uuid.uuid4()
    safe_name = Path(file_name).name
    storage_key = f"workspaces/{wid}/documents/{doc_id}/{safe_name}"

    storage = StorageService()
    try:
        storage.upload_bytes(storage_key, content, mime_type)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to upload file to object storage")
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {exc}") from exc

    document = Document(
        id=doc_id,
        workspace_id=wid,
        file_name=file_name,
        mime_type=mime_type,
        storage_key=storage_key,
        status=DocumentStatus.processing,
        tags=[],
    )
    db.add(document)
    db.commit()

    try:
        gemini_api_key = _extract_api_key_header(request, "x-gemini-api-key")
        background_tasks.add_task(
            process_document_ingestion,
            str(document.id),
            gemini_api_key=gemini_api_key,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to start background ingestion task")
        document.status = DocumentStatus.failed
        document.fail_reason = f"background_task_failed: {exc}"
        db.add(document)
        db.commit()

    return UploadResponse(doc_id=document.id)


@router.post(
    "/docs/import-drive-folder",
    response_model=DriveImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_drive_folder(
    wid: uuid.UUID,
    payload: DriveImportRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> DriveImportResponse:
    _ensure_workspace(db, wid)

    try:
        folder_id = extract_drive_folder_id(payload.folder_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    settings = get_settings()
    if not settings.google_drive_service_account_path:
        raise HTTPException(
            status_code=503,
            detail="Google Drive service account path is not configured on the server",
        )

    try:
        with open(settings.google_drive_service_account_path, "r", encoding="utf-8") as handle:
            service_account_info = json.load(handle)
    except OSError as exc:
        logger.exception("Failed to read Google Drive service account file")
        raise HTTPException(status_code=503, detail=f"Google Drive credentials are unavailable: {exc}") from exc

    drive = DriveService(service_account_info)
    try:
        video_files = filter_video_files(drive.list_files_in_folder(folder_id))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to list Google Drive folder contents")
        raise HTTPException(status_code=502, detail=f"Google Drive folder could not be read: {exc}") from exc

    if not video_files:
        raise HTTPException(
            status_code=404,
            detail="指定したフォルダ内に取り込み対象の動画ファイルが見つかりませんでした。",
        )

    gemini_api_key = _extract_api_key_header(request, "x-gemini-api-key")
    queued_count = 0
    skipped_count = 0
    doc_ids: list[uuid.UUID] = []

    for item in video_files:
        file_id = str(item.get("id") or "").strip()
        if not file_id:
            skipped_count += 1
            continue

        file_name = str(item.get("name") or f"drive-file-{file_id}")
        mime_type = str(item.get("mimeType") or mimetypes.guess_type(file_name)[0] or "application/octet-stream")
        storage_key = f"drive://{file_id}"

        existing = db.scalar(
            select(Document).where(Document.workspace_id == wid, Document.storage_key == storage_key)
        )
        if existing:
            if existing.status == DocumentStatus.failed:
                existing.file_name = file_name
                existing.mime_type = mime_type
                existing.status = DocumentStatus.processing
                existing.fail_reason = None
                existing.tags = sorted(set((existing.tags or []) + ["google-drive", "folder-import"]))
                db.add(existing)
                db.commit()
                background_tasks.add_task(
                    process_document_ingestion,
                    str(existing.id),
                    gemini_api_key=gemini_api_key,
                )
                queued_count += 1
                doc_ids.append(existing.id)
            else:
                skipped_count += 1
            continue

        document = Document(
            id=uuid.uuid4(),
            workspace_id=wid,
            file_name=file_name,
            mime_type=mime_type,
            storage_key=storage_key,
            status=DocumentStatus.processing,
            tags=["google-drive", "folder-import"],
        )
        db.add(document)
        db.commit()

        background_tasks.add_task(
            process_document_ingestion,
            str(document.id),
            gemini_api_key=gemini_api_key,
        )
        queued_count += 1
        doc_ids.append(document.id)

    return DriveImportResponse(
        folder_id=folder_id,
        queued_count=queued_count,
        skipped_count=skipped_count,
        doc_ids=doc_ids,
    )


@router.get("/docs/{doc_id}", response_model=DocumentResponse)
def get_document(wid: uuid.UUID, doc_id: uuid.UUID, db: Session = Depends(get_db)) -> Document:
    document = _get_document(db, wid, doc_id)
    return document


@router.delete("/docs/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(wid: uuid.UUID, doc_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    document = _get_document(db, wid, doc_id)

    storage = StorageService()
    try:
        storage.delete_object(document.storage_key)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to delete file from object storage")
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {exc}") from exc

    db.delete(document)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/docs/{doc_id}/ingestion-report", response_model=IngestionReportResponse)
def get_ingestion_report(
    wid: uuid.UUID,
    doc_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> IngestionRun:
    _get_document(db, wid, doc_id)
    stmt = (
        select(IngestionRun)
        .where(IngestionRun.document_id == doc_id)
        .order_by(IngestionRun.started_at.desc())
        .limit(1)
    )
    report = db.scalars(stmt).first()
    if not report:
        raise HTTPException(status_code=404, detail="Ingestion report not found")
    return report


@router.get("/docs/{doc_id}/presigned-url", response_model=PresignedUrlResponse)
def get_document_presigned_url(
    wid: uuid.UUID,
    doc_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PresignedUrlResponse:
    document = _get_document(db, wid, doc_id)
    storage = StorageService()
    try:
        url = storage.generate_presigned_get_url(document.storage_key)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to create presigned URL")
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {exc}") from exc
    return PresignedUrlResponse(url=url)


@router.get("/chunks/{chunk_id}", response_model=ChunkResponse)
def get_chunk(wid: uuid.UUID, chunk_id: uuid.UUID, db: Session = Depends(get_db)) -> Chunk:
    stmt = select(Chunk).where(Chunk.id == chunk_id, Chunk.workspace_id == wid)
    chunk = db.scalars(stmt).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk


def _ensure_workspace(db: Session, wid: uuid.UUID) -> Workspace:
    workspace = db.get(Workspace, wid)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


def _get_document(db: Session, wid: uuid.UUID, doc_id: uuid.UUID) -> Document:
    stmt = select(Document).where(Document.id == doc_id, Document.workspace_id == wid)
    document = db.scalars(stmt).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def _extract_api_key_header(request: Request, header_name: str) -> str | None:
    value = request.headers.get(header_name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
