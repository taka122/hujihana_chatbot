from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Select, func, literal, or_, select
from sqlalchemy.orm import Session

from app.models import Chunk, Document, DocumentStatus
from app.services.embed import EmbeddingService
from app.services.text_decode import is_probably_garbled_text


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
    mime_type: str


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
    title_rows = _run_title_search(db, workspace_id, query, max(final_k, 8))

    vec_norm = _normalize_scores({row[0].id: float(row[1] or 0.0) for row in vector_rows})
    kw_norm = _normalize_scores({row[0].id: float(row[1] or 0.0) for row in keyword_rows})
    title_norm = _normalize_scores({row[0].id: float(row[1] or 0.0) for row in title_rows})

    merged: dict[uuid.UUID, RetrievedChunk] = {}

    for chunk, raw_score, file_name, storage_key, mime_type in vector_rows:
        cid = chunk.id
        score = vec_norm.get(cid, float(raw_score or 0.0))
        merged[cid] = _to_retrieved(chunk, file_name, storage_key, mime_type, score, raw_score=float(raw_score or 0.0))

    for chunk, raw_score, file_name, storage_key, mime_type in keyword_rows:
        cid = chunk.id
        score = kw_norm.get(cid, float(raw_score or 0.0))
        raw_kw_score = min(max(float(raw_score or 0.0), 0.0), 1.0)
        if cid in merged:
            merged[cid].score = max(merged[cid].score, score)
            merged[cid].raw_score = max(merged[cid].raw_score, raw_kw_score)
        else:
            merged[cid] = _to_retrieved(chunk, file_name, storage_key, mime_type, score, raw_score=raw_kw_score)

    for chunk, raw_score, file_name, storage_key, mime_type in title_rows:
        cid = chunk.id
        score = max(title_norm.get(cid, float(raw_score or 0.0)), float(raw_score or 0.0))
        raw_title_score = min(max(float(raw_score or 0.0), 0.0), 1.0)
        if cid in merged:
            merged[cid].score = max(merged[cid].score, score)
            merged[cid].raw_score = max(merged[cid].raw_score, raw_title_score)
        else:
            merged[cid] = _to_retrieved(chunk, file_name, storage_key, mime_type, score, raw_score=raw_title_score)

    items = list(merged.values())
    for item in items:
        bonus = _query_alignment_bonus(query, item.file_name, item.section_title, item.snippet)
        penalty = 0.35 if is_probably_garbled_text(f"{item.file_name}\n{item.snippet}\n{item.text[:800]}") else 0.0
        item.score = max(0.0, min(1.5, item.score + bonus - penalty))

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

    stmt: Select[tuple[Chunk, float, str, str, str]] = (
        select(Chunk, score_expr, Document.file_name, Document.storage_key, Document.mime_type)
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

    stmt: Select[tuple[Chunk, float, str, str, str]] = (
        select(Chunk, rank, Document.file_name, Document.storage_key, Document.mime_type)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.workspace_id == workspace_id)
        .where(Document.status == DocumentStatus.ready)
        .where(Chunk.fts.op("@@")(ts_query))
        .order_by(rank.desc())
        .limit(top_k)
    )
    return list(db.execute(stmt).all())


def _run_title_search(
    db: Session,
    workspace_id: uuid.UUID,
    query: str,
    top_k: int,
) -> list[tuple[Chunk, float, str, str]]:
    fragments = _query_fragments(query)
    if not fragments:
        return []

    conditions = [func.lower(Document.file_name).contains(fragment) for fragment in fragments]
    stmt: Select[tuple[Chunk, float, str, str, str]] = (
        select(Chunk, literal(1.0).label("score"), Document.file_name, Document.storage_key, Document.mime_type)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.workspace_id == workspace_id)
        .where(Document.status == DocumentStatus.ready)
        .where(or_(*conditions))
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


def _query_alignment_bonus(query: str, file_name: str, section_title: str | None, snippet: str) -> float:
    query_norm = _normalize_match_text(query)
    if not query_norm:
        return 0.0

    title = _normalize_match_text(Path(file_name).stem)
    section = _normalize_match_text(section_title or "")
    snippet_text = _normalize_match_text(snippet)
    haystack = " ".join(part for part in [title, section, snippet_text] if part)

    query_tokens = _significant_tokens(query_norm)
    if not query_tokens:
        return 0.0

    token_hits = sum(1 for token in query_tokens if token in haystack)
    bonus = min(0.24, token_hits * 0.06)

    if title and (title in query_norm or any(token in title for token in query_tokens)):
        bonus += 0.18
    if section and any(token in section for token in query_tokens):
        bonus += 0.06

    return min(0.45, bonus)


def _normalize_match_text(text: str) -> str:
    lowered = (text or "").lower()
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠]+", "", lowered)


def _query_fragments(query: str) -> list[str]:
    normalized = _normalize_match_text(query)
    if not normalized:
        return []

    simplified = normalized
    for phrase in ["について", "教えて", "ください", "流れ", "手順", "方法", "確認", "とは", "ですか"]:
        simplified = simplified.replace(phrase, "")
    simplified = simplified.strip("のをはがにへと")

    fragments = [fragment for fragment in [simplified, normalized] if len(fragment) >= 2]
    return list(dict.fromkeys(fragments))


def _significant_tokens(text: str) -> list[str]:
    raw_tokens = re.findall(r"[0-9a-zぁ-んァ-ヶ一-龠]{2,}", text)
    stop_words = {"について", "ください", "教えて", "流れ", "手順", "方法", "確認", "こと"}
    tokens = [token for token in raw_tokens if token not in stop_words]
    return list(dict.fromkeys(tokens))


def _to_retrieved(chunk: Chunk, file_name: str, storage_key: str, mime_type: str, score: float, raw_score: float) -> RetrievedChunk:
    is_video = mime_type.startswith("video/")

    if is_video:
        ref_type = "video"
        if chunk.page_start is not None:
            m = chunk.page_start // 60
            s = chunk.page_start % 60
            ref = f"{m:02d}:{s:02d}"
        else:
            ref = "冒頭"
    elif chunk.page_start is not None:
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
        mime_type=mime_type,
    )
