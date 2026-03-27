from __future__ import annotations

import logging
import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Chunk, Document, DocumentStatus, IngestionRun, Workspace
from app.schemas import (
    ChunkResponse,
    DocumentResponse,
    IngestionReportResponse,
    PresignedUrlResponse,
    UploadResponse,
)
from app.services.queue import enqueue_ingestion
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
        enqueue_ingestion(
            str(document.id),
            gemini_api_key=gemini_api_key,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to enqueue ingestion job")
        document.status = DocumentStatus.failed
        document.fail_reason = f"enqueue_failed: {exc}"
        db.add(document)
        db.commit()

    return UploadResponse(doc_id=document.id)


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
