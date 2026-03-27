from typing import List, Optional

from care_rag_poc.models import ChatResult, ConversationState, ScoredFacility
from care_rag_poc.rag_types import RagResponder
from care_rag_poc.retriever import FacilityRetriever


class CareRagChatEngine:
    def __init__(
        self,
        retriever: FacilityRetriever,
        rag_responder: Optional[RagResponder] = None,
    ) -> None:
        self._retriever = retriever
        self._rag_responder = rag_responder
        self._state = ConversationState()

    def ask(self, user_message: str, top_k: int = 3) -> ChatResult:
        intent = self._retriever.parse_intent(user_message, state=self._state)

        if self._needs_clarification(intent):
            return ChatResult(
                text=(
                    "条件が不足しているため候補を絞れませんでした。\n"
                    "地域（例: 世田谷区）かサービス種別（例: デイサービス）を教えてください。"
                ),
                intent=intent,
                candidates=[],
            )

        candidates = self._retriever.retrieve(intent, top_k=top_k)
        strong = [item for item in candidates if item.score >= 2.0]
        if not strong:
            return ChatResult(
                text=(
                    "該当候補を十分な根拠で提示できませんでした（不明）。\n"
                    "地域やサービス種別を具体化して再度お試しください。"
                ),
                intent=intent,
                candidates=[],
            )

        self._state.prefecture = intent.prefecture
        self._state.city = intent.city
        self._state.service_type = intent.service_type
        self._state.keywords = intent.keywords

        if self._rag_responder:
            rag_generation = self._rag_responder.generate(
                query=user_message,
                intent=intent,
                base_candidates=strong,
                top_k=top_k,
            )
            return ChatResult(
                text=rag_generation.text,
                intent=intent,
                candidates=rag_generation.candidates,
            )

        rendered = self._render_response(strong, intent.contact_requested)
        return ChatResult(text=rendered, intent=intent, candidates=strong)

    def reset_context(self) -> None:
        self._state = ConversationState()

    @staticmethod
    def _needs_clarification(intent) -> bool:
        if intent.city or intent.service_type:
            return False
        return len(intent.keywords) == 0

    @staticmethod
    def _render_response(candidates: List[ScoredFacility], with_phone: bool) -> str:
        lines = [f"候補を{len(candidates)}件見つけました。"]
        for i, candidate in enumerate(candidates, start=1):
            f = candidate.facility
            reason_text = " / ".join(candidate.reasons) if candidate.reasons else "一致条件なし"
            lines.append(
                f"{i}. {f.name}（{f.service_type}）\n"
                f"   地域: {f.prefecture}{f.city}\n"
                f"   住所: {f.address}\n"
                f"   営業: {f.business_hours}\n"
                f"   特徴: {', '.join(f.features)}\n"
                f"   根拠: {reason_text}\n"
                f"   ソース: {f.source_url} (ID: {f.facility_id})"
            )
            if with_phone:
                lines.append(f"   連絡先: {f.phone}")

        lines.append("注意: 最終的な空き状況・費用・受入可否は各事業所へ直接確認してください。")
        return "\n".join(lines)
