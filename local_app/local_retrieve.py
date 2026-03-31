"""Hybrid retrieval (vector + keyword) for the local app.

Vector search is implemented with pure numpy cosine similarity over all
stored embeddings.  Keyword search uses the SQLite FTS5 index.  Results
are merged with the same normalised-score strategy as the main app.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

import numpy as np

_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Shim must be installed before any app.* imports.
import local_app._shim  # noqa: F401

from app.services.embed import EmbeddingService
from local_app._shim import RetrievedChunk
from local_app.local_db import LocalDatabase


def local_hybrid_retrieve(
    db: LocalDatabase,
    query: str,
    gemini_api_key: str,
    top_k_vec: int = 10,
    top_k_kw: int = 10,
    final_k: int = 5,
) -> list[RetrievedChunk]:
    """Return up to *final_k* chunks most relevant to *query*."""
    embedder = EmbeddingService(gemini_api_key=gemini_api_key)
    query_vec = np.array(embedder.embed_query(query), dtype=np.float32)

    # ---- vector search ------------------------------------------------
    all_chunks = db.get_all_chunks()
    vec_results: list[tuple[dict[str, Any], float]] = []
    if all_chunks:
        matrix = np.array([c["embedding"] for c in all_chunks], dtype=np.float32)
        # Cosine similarity = dot(q, k) / (|q| |k|)
        norms = np.linalg.norm(matrix, axis=1)
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            sims = (matrix @ query_vec) / (norms * q_norm + 1e-9)
        else:
            sims = np.zeros(len(all_chunks), dtype=np.float32)
        top_idx = np.argsort(sims)[::-1][:top_k_vec]
        for idx in top_idx:
            vec_results.append((all_chunks[idx], float(sims[idx])))

    # ---- keyword search -----------------------------------------------
    try:
        kw_rows = db.search_fts(query, top_k_kw)
    except Exception:  # noqa: BLE001
        kw_rows = []

    # ---- merge --------------------------------------------------------
    vec_norm = _normalize({r["id"]: sc for r, sc in vec_results})
    # FTS5 bm25 scores are negative (lower = better)
    kw_norm = _normalize_kw({r["id"]: r["score"] for r in kw_rows})

    merged: dict[str, RetrievedChunk] = {}

    for chunk, raw_score in vec_results:
        cid = chunk["id"]
        score = vec_norm.get(cid, raw_score)
        merged[cid] = _to_retrieved(chunk, score, raw_score)

    for row in kw_rows:
        cid = row["id"]
        score = kw_norm.get(cid, 0.5)
        if cid in merged:
            merged[cid].score = max(merged[cid].score, score)
        else:
            merged[cid] = _to_retrieved(row, score, score)

    items = sorted(merged.values(), key=lambda x: x.score, reverse=True)
    return items[:final_k]


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _normalize(raw: dict[str, float]) -> dict[str, float]:
    if not raw:
        return {}
    values = list(raw.values())
    lo, hi = min(values), max(values)
    if hi == lo:
        return {k: 1.0 for k in raw}
    return {k: (v - lo) / (hi - lo) for k, v in raw.items()}


def _normalize_kw(raw: dict[str, float]) -> dict[str, float]:
    """Normalise keyword search scores (LIKE search returns constant 1.0)."""
    return _normalize(raw)


def _to_retrieved(chunk: dict[str, Any], score: float, raw_score: float) -> RetrievedChunk:
    page_start = chunk.get("page_start")
    page_end = chunk.get("page_end")
    section_title = chunk.get("section_title")

    if page_start is not None:
        if page_end and page_end != page_start:
            ref = f"p.{page_start}-{page_end}"
        else:
            ref = f"p.{page_start}"
    elif section_title:
        ref = f"section:{section_title}"
    else:
        ref = "section:unknown"

    text = chunk.get("text", "")
    snippet = chunk.get("snippet") or text[:300]

    return RetrievedChunk(
        chunk_id=uuid.UUID(chunk["id"]),
        document_id=uuid.UUID(chunk["document_id"]),
        file_name=chunk.get("file_name", ""),
        ref_type="page",
        ref=ref,
        snippet=snippet,
        text=text,
        page_start=page_start,
        page_end=page_end,
        section_title=section_title,
        score=score,
        raw_score=raw_score,
    )
