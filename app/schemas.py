from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import DocumentStatus


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    file_name: str
    mime_type: str
    storage_key: str
    status: DocumentStatus
    page_count: int | None
    tags: list[str]
    fail_reason: str | None
    created_at: datetime
    updated_at: datetime


class IngestionReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    started_at: datetime
    finished_at: datetime | None
    extracted_pages: int
    failed_pages_count: int
    failed_pages: list[dict]
    ocr_used_pages: list[int]
    chunk_count: int
    estimated_cost: float | None
    log: dict | None


class UploadResponse(BaseModel):
    doc_id: uuid.UUID


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    workspace_id: uuid.UUID
    text: str
    snippet: str | None
    page_start: int | None
    page_end: int | None
    section_title: str | None


class PresignedUrlResponse(BaseModel):
    url: str


class ChatQueryRequest(BaseModel):
    query: str = Field(min_length=1)


class ChatAnswerPayload(BaseModel):
    conclusion: str
    details: str
    notes: str
    next_actions: list[str]


class ChatCitation(BaseModel):
    doc_id: uuid.UUID
    file_name: str
    ref_type: Literal["page", "slide", "sheet"]
    ref: str
    snippet: str
    score: float | None
    chunk_id: uuid.UUID


class ChatQueryResponse(BaseModel):
    answer: ChatAnswerPayload
    citations: list[ChatCitation]
