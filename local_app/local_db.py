"""SQLite-backed local store for the standalone local app.

Documents and their chunks (with embedding vectors stored as JSON) are kept
in a single SQLite database file.  An FTS5 virtual table provides keyword
search without any external dependencies.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    file_name   TEXT NOT NULL,
    mime_type   TEXT NOT NULL,
    file_path   TEXT,           -- absolute path to locally-saved file
    status      TEXT NOT NULL DEFAULT 'processing',
    page_count  INTEGER,
    tags        TEXT NOT NULL DEFAULT '[]',
    fail_reason TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chunks (
    id            TEXT PRIMARY KEY,
    document_id   TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index   INTEGER NOT NULL,
    text          TEXT NOT NULL,
    snippet       TEXT,
    page_start    INTEGER,
    page_end      INTEGER,
    section_title TEXT,
    embedding     TEXT NOT NULL,   -- JSON array of floats
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
"""


class LocalDatabase:
    """Thin wrapper around a SQLite connection."""

    def __init__(self, db_path: str | Path = "local_app/data/local.db") -> None:
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _migrate(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def add_document(
        self,
        *,
        doc_id: str,
        file_name: str,
        mime_type: str,
        file_path: str | None = None,
        status: str = "processing",
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO documents (id, file_name, mime_type, file_path, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (doc_id, file_name, mime_type, file_path, status),
        )
        self._conn.commit()

    def update_document_status(
        self,
        doc_id: str,
        *,
        status: str,
        page_count: int | None = None,
        tags: list[str] | None = None,
        fail_reason: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE documents
            SET status = ?,
                page_count = COALESCE(?, page_count),
                tags = COALESCE(?, tags),
                fail_reason = ?
            WHERE id = ?
            """,
            (
                status,
                page_count,
                json.dumps(tags) if tags is not None else None,
                fail_reason,
                doc_id,
            ),
        )
        self._conn.commit()

    def list_documents(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM documents ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_document(self, doc_id: str) -> None:
        row = self._conn.execute(
            "SELECT file_path FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if row and row["file_path"]:
            try:
                Path(row["file_path"]).unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                logger.warning("Could not delete local file: %s", row["file_path"])

        self._conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self._conn.commit()

    # ------------------------------------------------------------------
    # Chunks
    # ------------------------------------------------------------------

    def add_chunks(
        self,
        doc_id: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        """Insert chunk rows."""
        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            chunk["id"] = chunk_id
            self._conn.execute(
                """
                INSERT INTO chunks
                    (id, document_id, chunk_index, text, snippet,
                     page_start, page_end, section_title, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk_id,
                    doc_id,
                    chunk["chunk_index"],
                    chunk["text"],
                    chunk.get("snippet"),
                    chunk.get("page_start"),
                    chunk.get("page_end"),
                    chunk.get("section_title"),
                    json.dumps(chunk["embedding"]),
                ),
            )
        self._conn.commit()

    def get_all_chunks(self) -> list[dict[str, Any]]:
        """Return all chunk rows with file_name joined from documents."""
        rows = self._conn.execute(
            """
            SELECT c.*, d.file_name
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.status = 'ready'
            """
        ).fetchall()
        result = []
        for r in rows:
            row_dict = dict(r)
            row_dict["embedding"] = json.loads(row_dict["embedding"])
            result.append(row_dict)
        return result

    def search_fts(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Keyword search using LIKE for reliable Japanese text support."""
        tokens = [t.strip() for t in query.split() if t.strip()]
        if not tokens:
            return []

        # Build WHERE clause: all tokens must appear in text (AND logic)
        like_clauses = " AND ".join(["c.text LIKE ?" for _ in tokens])
        params = [f"%{t}%" for t in tokens]
        params.append(top_k)

        rows = self._conn.execute(
            f"""
            SELECT c.id, c.document_id, c.chunk_index, c.text, c.snippet,
                   c.page_start, c.page_end, c.section_title,
                   d.file_name,
                   1.0 AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.status = 'ready' AND {like_clauses}
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]
