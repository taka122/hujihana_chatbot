"""Document ingestion pipeline for the local app.

Reuses the existing ``app.services.ingest`` parsing logic and
``app.services.embed`` for Gemini embeddings, but stores results in
the lightweight SQLite backend instead of PostgreSQL + pgvector.
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from pathlib import Path

# Allow running from repo root as well as from local_app/ directory.
_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Shim must be installed before any app.* imports.
import local_app._shim  # noqa: F401

from app.services.embed import EmbeddingService
from app.services.ingest import IngestionError, UnsupportedDocumentError, build_chunks, parse_document
from local_app.local_db import LocalDatabase

logger = logging.getLogger(__name__)


def ingest_document(
    *,
    file_name: str,
    mime_type: str,
    data: bytes,
    gemini_api_key: str,
    db: LocalDatabase,
    save_dir: str | Path | None = None,
) -> str:
    """Parse, embed, and store a document.  Returns the new document UUID."""
    doc_id = str(uuid.uuid4())

    # Optionally save the raw file to the local filesystem.
    file_path: str | None = None
    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file_name).name
        dest = save_dir / f"{doc_id}_{safe_name}"
        dest.write_bytes(data)
        file_path = str(dest)

    db.add_document(
        doc_id=doc_id,
        file_name=file_name,
        mime_type=mime_type,
        file_path=file_path,
        status="processing",
    )

    # --- Set GEMINI_API_KEY so app.config.get_settings() can read it ----
    _prev_key = os.environ.get("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = gemini_api_key

    try:
        # 1. Parse document into TextBlocks
        parse_result = parse_document(
            file_name=file_name,
            mime_type=mime_type,
            data=data,
            gemini_api_key_override=gemini_api_key,
        )

        # 2. Split into chunks
        chunk_payloads = build_chunks(parse_result.blocks)
        if not chunk_payloads:
            raise IngestionError("No text could be extracted from the document.")

        # 3. Embed
        embedder = EmbeddingService(gemini_api_key=gemini_api_key)
        texts = [c.text for c in chunk_payloads]
        vectors = embedder.embed_texts(texts)

        # 4. Build chunk dicts and persist
        chunks = []
        for idx, (cp, vec) in enumerate(zip(chunk_payloads, vectors)):
            chunks.append(
                {
                    "chunk_index": idx,
                    "text": cp.text,
                    "snippet": cp.snippet,
                    "page_start": cp.page_start,
                    "page_end": cp.page_end,
                    "section_title": cp.section_title,
                    "embedding": vec,
                }
            )
        db.add_chunks(doc_id, chunks)
        db.update_document_status(
            doc_id,
            status="ready",
            page_count=parse_result.page_count,
            tags=parse_result.tags,
        )
        logger.info("Ingested %d chunks from %s", len(chunks), file_name)

    except (IngestionError, UnsupportedDocumentError) as exc:
        db.update_document_status(doc_id, status="failed", fail_reason=str(exc))
        logger.warning("Ingestion failed for %s: %s", file_name, exc)
        raise

    except Exception as exc:  # noqa: BLE001
        db.update_document_status(doc_id, status="failed", fail_reason=f"{type(exc).__name__}: {exc}")
        logger.exception("Unexpected ingestion error for %s", file_name)
        raise

    finally:
        # Restore env
        if _prev_key is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = _prev_key

    return doc_id
