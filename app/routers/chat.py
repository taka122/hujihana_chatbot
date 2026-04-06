from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Chunk, Workspace
from app.schemas import ChatQueryRequest, ChatQueryResponse
from app.services.answer import AnswerService
from app.services.embed import EmbeddingService
from app.services.retrieve import hybrid_retrieve
from app.services.storage import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{wid}", tags=["chat"])


@router.post("/chat/query", response_model=ChatQueryResponse)
def query_chat(
    wid: uuid.UUID,
    payload: ChatQueryRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ChatQueryResponse:
    _ensure_workspace(db, wid)
    settings = get_settings()
    gemini_api_key = _extract_api_key_header(request, "x-gemini-api-key")

    try:
        embedder = EmbeddingService(gemini_api_key=gemini_api_key)
        retrieved = hybrid_retrieve(
            db=db,
            workspace_id=wid,
            query=payload.query,
            embedder=embedder,
            top_k_vec=settings.vector_top_k,
            top_k_kw=settings.keyword_top_k,
            final_k=settings.answer_context_chunks,
        )

        answer_service = AnswerService(gemini_api_key=gemini_api_key)
        result = answer_service.answer(
            query=payload.query,
            contexts=retrieved,
            min_score=settings.retrieval_score_threshold,
        )

        citation_ids = [item["chunk_id"] for item in result.citations]
        if citation_ids:
            valid_ids = set(
                db.scalars(
                    select(Chunk.id)
                    .where(Chunk.workspace_id == wid)
                    .where(Chunk.id.in_(citation_ids))
                ).all()
            )
            result.citations = [item for item in result.citations if item["chunk_id"] in valid_ids]
            if not result.citations:
                result = answer_service.not_found()
            else:
                # Generate presigned URLs for citations
                storage = StorageService()
                for item in result.citations:
                    skey = item.get("storage_key")
                    if skey:
                        item["url"] = storage.generate_presigned_get_url(skey)

        return ChatQueryResponse(answer=result.answer, citations=result.citations)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat query failed")
        fallback = {
            "answer": {
                "conclusion": "ソース内に該当情報が見つかりませんでした。",
                "details": "検索または回答処理に失敗したため、断定を避けて回答を保留しました。",
                "notes": f"internal_error: {type(exc).__name__}",
                "next_actions": [
                    "少し表現を変えて再質問してください。",
                    "必要な資料が未投入ならアップロードしてください。",
                ],
            },
            "citations": [],
        }
        return ChatQueryResponse(**fallback)


def _ensure_workspace(db: Session, wid: uuid.UUID) -> Workspace:
    workspace = db.get(Workspace, wid)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


def _extract_api_key_header(request: Request, header_name: str) -> str | None:
    value = request.headers.get(header_name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
