"""initial schema for universal rag poc

Revision ID: 20260218_0001
Revises:
Create Date: 2026-02-18 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260218_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    document_status = postgresql.ENUM("processing", "ready", "failed", name="document_status", create_type=False)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_status') THEN
                CREATE TYPE document_status AS ENUM ('processing', 'ready', 'failed');
            END IF;
        END $$;
        """
    )

    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("status", document_status, nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("fail_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extracted_pages", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_pages_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failed_pages", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("ocr_used_pages", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("log", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("section_title", sa.Text(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("fts", postgresql.TSVECTOR(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_chunks_workspace_document", "chunks", ["workspace_id", "document_id"])
    op.create_index("ix_documents_workspace_status", "documents", ["workspace_id", "status"])
    op.create_index("ix_chunks_fts", "chunks", ["fts"], postgresql_using="gin")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_ivfflat "
        "ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    op.execute(
        """
        CREATE FUNCTION chunks_fts_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.fts := to_tsvector('simple', coalesce(NEW.text, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER chunks_fts_update
        BEFORE INSERT OR UPDATE OF text ON chunks
        FOR EACH ROW EXECUTE FUNCTION chunks_fts_trigger();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS chunks_fts_update ON chunks")
    op.execute("DROP FUNCTION IF EXISTS chunks_fts_trigger")
    op.drop_index("ix_chunks_embedding_ivfflat", table_name="chunks")
    op.drop_index("ix_chunks_fts", table_name="chunks")
    op.drop_index("ix_documents_workspace_status", table_name="documents")
    op.drop_index("ix_chunks_workspace_document", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("ingestion_runs")
    op.drop_table("documents")
    op.drop_table("workspaces")
    op.execute("DROP TYPE IF EXISTS document_status")
