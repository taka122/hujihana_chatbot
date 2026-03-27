from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DocumentStatus(str, enum.Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    documents: Mapped[list["Document"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), nullable=False, default=DocumentStatus.processing
    )
    page_count: Mapped[int | None] = mapped_column(Integer)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    fail_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    workspace: Mapped[Workspace] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    ingestion_runs: Mapped[list["IngestionRun"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_pages_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_pages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    ocr_used_pages: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost: Mapped[float | None] = mapped_column(Float)
    log: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    document: Mapped[Document] = relationship(back_populates="ingestion_runs")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    section_title: Mapped[str | None] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text)
    fts: Mapped[str] = mapped_column(TSVECTOR, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")
