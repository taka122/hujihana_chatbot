from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.config import get_settings
from app.services.gemini_client import GeminiApiError, GeminiClient
from app.services.retrieve import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class AnswerResult:
    answer: dict
    citations: list[dict]


class AnswerService:
    def __init__(self, gemini_api_key: str | None = None) -> None:
        self._settings = get_settings()
        self._provider = self._settings.llm_provider.lower()
        self._model = self._settings.llm_model

        if self._provider != "gemini":
            raise RuntimeError(f"Unsupported LLM provider in Gemini-only mode: {self._provider}")

        api_key = _normalize_api_key(gemini_api_key) or self._settings.gemini_api_key
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required in Gemini-only mode")
        self._gemini_client = GeminiClient(api_key=api_key, base_url=self._settings.gemini_base_url)

    def answer(self, query: str, contexts: list[RetrievedChunk], min_score: float) -> AnswerResult:
        if not contexts or max(item.raw_score for item in contexts) < min_score:
            return self._not_found()

        context_map = {str(item.chunk_id): item for item in contexts}

        parsed = self._parse_with_retry(raw_getter=lambda: self._generate_gemini(query, contexts))
        if not parsed:
            logger.warning("Gemini JSON parse failed repeatedly. Falling back to extractive response.")
            return self._mock_answer(query, contexts)

        answer = parsed.get("answer", {}) if isinstance(parsed, dict) else {}
        answer_payload = {
            "conclusion": str(answer.get("conclusion", "")) or "ソースから結論を確定できませんでした。",
            "details": str(answer.get("details", "")),
            "notes": str(answer.get("notes", "")),
            "next_actions": [str(item) for item in answer.get("next_actions", []) if str(item).strip()],
        }

        cited_ids = []
        for item in parsed.get("citations", []) if isinstance(parsed, dict) else []:
            if not isinstance(item, dict):
                continue
            chunk_id = str(item.get("chunk_id", "")).strip()
            if chunk_id and chunk_id in context_map:
                cited_ids.append(chunk_id)

        deduped_ids = list(dict.fromkeys(cited_ids))
        citations = [self._to_citation(context_map[cid]) for cid in deduped_ids]
        if not citations:
            return self._not_found()

        return AnswerResult(answer=answer_payload, citations=citations)

    def not_found(self) -> AnswerResult:
        return self._not_found()

    def _generate_gemini(self, query: str, contexts: list[RetrievedChunk]) -> str:
        context_text = "\n\n".join(
            [
                (
                    f"[chunk_id={item.chunk_id}]\n"
                    f"file_name={item.file_name}\n"
                    f"ref={item.ref}\n"
                    f"score={item.score:.3f}\n"
                    f"snippet={item.snippet}\n"
                    f"text={item.text[:2400]}"
                )
                for item in contexts
            ]
        )

        system_prompt = (
            "あなたは業務文書・動画要約用の高精度RAG回答器です。\n"
            "- 【重要】ユーザーの質問が単語のみで曖昧な場合（例：「会計」）でも、単に聞き返すだけでなく、資料から読み取れる全体像や概要を「簡潔な回答」として提示してください。\n"
            "- 【重要】回答は情報量が多くなりすぎないよう、まずは概要のみをシンプルに答えることを基本としてください。\n"
            "- 概要を提示した上で、ユーザーがさらに詳細を絞り込めるように、次のアクション（おすすめの質問）を提示してください。\n"
            "- 与えられたcontextsだけを根拠に、日本語で正確に回答を作成してください。\n"
            "- 重複する内容は統合し、ソースにない情報は補完せず『不明』『資料記載なし』と明示してください。\n"
            "- citations には、回答作成に使った根拠の chunk_id を含めてください（根拠を使わない場合は空配列 [] にしてください）。\n"
            "- どのような場合でも、必ず指定されたJSON形式のみを返し、前後の説明文やコードブロックは一切付けないでください。"
        )
        user_prompt = (
            f"query:\n{query}\n\n"
            f"contexts_count: {len(contexts)}\n\n"
            f"contexts:\n{context_text}\n\n"
            "出力方針:\n"
            "1. conclusion: 質問に対する最も重要な結論、または資料から分かる全体像・概要を短く明快に書く。\n"
            "2. details: 簡潔な要点のみをまとめる（長文になりすぎる場合は省略し、詳細は次の質問に委ねる）。\n"
            "3. notes: 前提条件や不明点、または「気になる項目をクリックして詳細を確認してください」等の案内を書く。\n"
            "4. next_actions: ユーザーがそのままクリックして深掘りできる「関連する質問」や「絞り込みのための質問」を最大3件で書く。\n\n"
            "以下のJSONスキーマに厳密準拠して返答してください:\n"
            "{\n"
            "  \"answer\": {\n"
            "    \"conclusion\": \"...\",\n"
            "    \"details\": \"...\",\n"
            "    \"notes\": \"...\",\n"
            "    \"next_actions\": [\"...\"]\n"
            "  },\n"
            "  \"citations\": [\n"
            "    {\"chunk_id\": \"uuid\"}\n"
            "  ]\n"
            "}"
        )
        try:
            return self._gemini_client.generate_content(self._model, system_prompt, user_prompt)
        except GeminiApiError as exc:
            raise RuntimeError(str(exc)) from exc

    def _parse_with_retry(self, raw_getter, attempts: int = 3) -> dict | None:
        for _ in range(attempts):
            try:
                raw = raw_getter()
                return self._safe_json_loads(raw)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to parse LLM JSON output")
                continue
        return None

    def _safe_json_loads(self, raw: str) -> dict:
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
            stripped = re.sub(r"```$", "", stripped).strip()
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError("LLM output is not a JSON object")
        return parsed

    def _mock_answer(self, query: str, contexts: list[RetrievedChunk]) -> AnswerResult:
        # LLM unavailable時の安全フォールバック。断定せず、引用ベースの要約だけ返す。
        top = contexts[: min(12, len(contexts))]
        details = "\n".join([f"- {item.file_name} {item.ref}: {item.snippet}" for item in top])
        answer = {
            "conclusion": "該当しうる情報をソースから抽出しました。断定が必要な場合は原文確認が必要です。",
            "details": details,
            "notes": "LLM応答器の代わりに抽出ベースで回答しました。",
            "next_actions": ["引用元ドキュメントを確認し、必要なら追加資料をアップロードしてください。"],
        }
        return AnswerResult(answer=answer, citations=[self._to_citation(item) for item in top])

    def _not_found(self) -> AnswerResult:
        return AnswerResult(
            answer={
                "conclusion": "ソース内に該当情報が見つかりませんでした。",
                "details": "現在の資料群には質問に直接対応する根拠がありません。",
                "notes": "断定を避けるため回答を保留しました。",
                "next_actions": [
                    "該当規程名やマニュアル章を含む資料を追加してください。",
                    "対象部署・期間・対象サービスを明示して再質問してください。",
                    "表データが必要な場合はCSV/XLSX原本または抽出済みTXTを追加してください。",
                ],
            },
            citations=[],
        )

    @staticmethod
    def _to_citation(item: RetrievedChunk) -> dict:
        return {
            "doc_id": item.document_id,
            "file_name": item.file_name,
            "ref_type": item.ref_type,
            "ref": item.ref,
            "snippet": item.snippet,
            "score": item.score,
            "chunk_id": item.chunk_id,
            "storage_key": item.storage_key,
            "mime_type": item.mime_type,
        }


def _normalize_api_key(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
