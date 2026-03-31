from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Chunk, Document, DocumentStatus
from app.services.embed import EmbeddingService


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    file_name: str
    ref_type: str
    ref: str
    snippet: str
    text: str
    page_start: int | None
    page_end: int | None
    section_title: str | None
    score: float
    raw_score: float
    storage_key: str


def hybrid_retrieve(
    db: Session,
    workspace_id: uuid.UUID,
    query: str,
    embedder: EmbeddingService,
    top_k_vec: int,
    top_k_kw: int,
    final_k: int,
) -> list[RetrievedChunk]:
    query_vector = embedder.embed_query(query)

    vector_rows = _run_vector_search(db, workspace_id, query_vector, top_k_vec)
    keyword_rows = _run_keyword_search(db, workspace_id, query, top_k_kw)

    vec_norm = _normalize_scores({row[0].id: float(row[1] or 0.0) for row in vector_rows})
    kw_norm = _normalize_scores({row[0].id: float(row[1] or 0.0) for row in keyword_rows})

    merged: dict[uuid.UUID, RetrievedChunk] = {}

    for chunk, raw_score, file_name, storage_key in vector_rows:
        cid = chunk.id
        score = vec_norm.get(cid, float(raw_score or 0.0))
        merged[cid] = _to_retrieved(chunk, file_name, storage_key, score, raw_score=float(raw_score or 0.0))

    for chunk, raw_score, file_name, storage_key in keyword_rows:
        cid = chunk.id
        score = kw_norm.get(cid, float(raw_score or 0.0))
        raw_kw_score = min(max(float(raw_score or 0.0), 0.0), 1.0)
        if cid in merged:
            merged[cid].score = max(merged[cid].score, score)
            merged[cid].raw_score = max(merged[cid].raw_score, raw_kw_score)
        else:
            merged[cid] = _to_retrieved(chunk, file_name, storage_key, score, raw_score=raw_kw_score)

    items = list(merged.values())
    items.sort(key=lambda item: item.score, reverse=True)
    return items[:final_k]


def _run_vector_search(
    db: Session,
    workspace_id: uuid.UUID,
    query_vector: list[float],
    top_k: int,
) -> list[tuple[Chunk, float, str]]:
    distance = Chunk.embedding.cosine_distance(query_vector)
    score_expr = (1 - distance).label("score")

    stmt: Select[tuple[Chunk, float, str, str]] = (
        select(Chunk, score_expr, Document.file_name, Document.storage_key)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.workspace_id == workspace_id)
        .where(Document.status == DocumentStatus.ready)
        .order_by(distance.asc())
        .limit(top_k)
    )
    return list(db.execute(stmt).all())


def _run_keyword_search(
    db: Session,
    workspace_id: uuid.UUID,
    query: str,
    top_k: int,
) -> list[tuple[Chunk, float, str]]:
    ts_query = func.plainto_tsquery("simple", query)
    rank = func.ts_rank_cd(Chunk.fts, ts_query).label("score")

    stmt: Select[tuple[Chunk, float, str, str]] = (
        select(Chunk, rank, Document.file_name, Document.storage_key)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.workspace_id == workspace_id)
        .where(Document.status == DocumentStatus.ready)
        .where(Chunk.fts.op("@@")(ts_query))
        .order_by(rank.desc())
        .limit(top_k)
    )
    return list(db.execute(stmt).all())


def _normalize_scores(raw: dict[uuid.UUID, float]) -> dict[uuid.UUID, float]:
    if not raw:
        return {}
    values = list(raw.values())
    min_score = min(values)
    max_score = max(values)
    if max_score == min_score:
        return {key: 1.0 for key in raw.keys()}
    return {key: (score - min_score) / (max_score - min_score) for key, score in raw.items()}


def _to_retrieved(chunk: Chunk, file_name: str, storage_key: str, score: float, raw_score: float) -> RetrievedChunk:
    if chunk.page_start is not None:
        ref_type = "page"
        if chunk.page_end and chunk.page_end != chunk.page_start:
            ref = f"p.{chunk.page_start}-{chunk.page_end}"
        else:
            ref = f"p.{chunk.page_start}"
    elif chunk.section_title:
        ref_type = "page"
        ref = f"section:{chunk.section_title}"
    else:
        ref_type = "page"
        ref = "section:unknown"

    return RetrievedChunk(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        file_name=file_name,
        ref_type=ref_type,
        ref=ref,
        snippet=chunk.snippet or (chunk.text[:300]),
        text=chunk.text,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        section_title=chunk.section_title,
        score=score,
        raw_score=raw_score,
        storage_key=storage_key,
    )
