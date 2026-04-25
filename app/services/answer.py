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
                    f"snippet={item.snippet}\n"
                    f"text={item.text[:2400]}"
                )
                for item in contexts
            ]
        )

        system_prompt = (
            "あなたは藤花歯科クリニックの業務マニュアルに基づくRAG回答器です。\n"
            "【最重要】回答は短く・簡潔に。受付スタッフが現場でサッと読める分量にする。\n"
            "\n"
            "出力ルール:\n"
            "- conclusion: 結論を1〜2文で簡潔に書く（最大120字、改行不可）\n"
            "- details: 必要最小限の補足のみ（最大100字、不要なら空文字 \"\"）\n"
            "    * 手順が多い場合も、主要ステップだけに絞る\n"
            "    * 「詳しく知りたい場合は再度質問してください」と添える程度でOK\n"
            "- notes: 注意点が本当にある場合のみ記入（最大80字、なければ空文字 \"\"）\n"
            "- next_actions: 本当に必要な次アクションがある時だけ1〜2個（なければ空配列 []）\n"
            "\n"
            "禁止事項:\n"
            "- ソースに書いていないことを断定しない\n"
            "- 引用のない断定は禁止\n"
            "- 同じ内容をconclusionとdetailsで繰り返さない\n"
            "- 一般論・前置き・お礼・絵文字・装飾記号を入れない\n"
            "\n"
            "形式:\n"
            "- citationsには必ずchunk_idを入れる\n"
            "- JSONのみを返す（前後の説明文・コードブロック禁止）"
        )
        user_prompt = (
            f"query:\n{query}\n\n"
            f"contexts:\n{context_text}\n\n"
            "以下のJSONスキーマに厳密準拠して返答してください。\n"
            "繰り返し: conclusionは最大120字、detailsは最大100字、簡潔さ最優先。\n"
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
        top = contexts[: min(3, len(contexts))]
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
        }


def _normalize_api_key(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
