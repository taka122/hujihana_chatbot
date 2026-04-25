"""曖昧クエリの判定 + 聞き返し候補生成。

判定方針:
- 検索結果（top_k）が3ファイル以上にまたがっていれば「曖昧」と扱う。
- 1〜2ファイルに集中していれば、ユーザーは具体的なものを聞いているとみなす。

候補生成方針:
- 散らばっているファイル（最大5）から、各ファイルの代表スニペットを集める。
- LLMに「ユーザーが選びやすい1問1答形式の選択肢を生成して」と指示してJSON配列で返させる。
- LLMが失敗したら、ファイル名そのものを候補にフォールバック。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.config import get_settings
from app.services.gemini_client import GeminiApiError, GeminiClient
from app.services.retrieve import RetrievedChunk

logger = logging.getLogger(__name__)

# 散らばり判定のしきい値（このファイル数以上にまたがれば曖昧）
SCATTER_THRESHOLD = 3

# 聞き返し候補の最大数
MAX_OPTIONS = 5

# 候補生成に使うファイルあたりの代表チャンク数
REP_CHUNKS_PER_FILE = 1


@dataclass
class ClarificationResult:
    needed: bool
    question: str
    options: list[str]


class ClarificationService:
    def __init__(self, gemini_api_key: str | None = None) -> None:
        self._settings = get_settings()
        self._model = self._settings.llm_model

        api_key = (gemini_api_key or "").strip() or self._settings.gemini_api_key
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for ClarificationService")
        self._gemini_client = GeminiClient(
            api_key=api_key,
            base_url=self._settings.gemini_base_url,
        )

    def evaluate(self, query: str, contexts: list[RetrievedChunk]) -> ClarificationResult:
        """検索結果を見て、曖昧判定 + 必要なら候補生成を行う。

        曖昧でなければ needed=False を返し、呼び出し側は通常回答に進む。
        """
        if not contexts:
            return ClarificationResult(needed=False, question="", options=[])

        # ファイル単位で集計
        files_in_results = self._unique_files_ordered(contexts)

        if len(files_in_results) < SCATTER_THRESHOLD:
            # 1〜2ファイルに集中 → 具体的な質問とみなす
            return ClarificationResult(needed=False, question="", options=[])

        # 曖昧判定：候補を生成
        try:
            options = self._generate_options(query, contexts, files_in_results)
        except Exception:  # noqa: BLE001
            logger.exception("Clarification option generation failed; falling back to file names")
            options = self._fallback_options(files_in_results)

        if not options:
            options = self._fallback_options(files_in_results)

        question = self._build_question(query)
        return ClarificationResult(needed=True, question=question, options=options[:MAX_OPTIONS])

    # ------------------------------------------------------------------ helpers

    def _unique_files_ordered(self, contexts: list[RetrievedChunk]) -> list[str]:
        seen: list[str] = []
        for item in contexts:
            name = item.file_name or ""
            if name and name not in seen:
                seen.append(name)
        return seen

    def _build_question(self, query: str) -> str:
        cleaned = query.strip()
        if not cleaned:
            return "もう少し詳しく教えてください。何について知りたいですか？"
        return f"「{cleaned}」について、どの内容を知りたいですか？"

    def _fallback_options(self, files: list[str]) -> list[str]:
        # ファイル名から拡張子と区切り記号を取り除いて、人間が読める形にする
        cleaned: list[str] = []
        for name in files[:MAX_OPTIONS]:
            base = re.sub(r"\.[A-Za-z0-9]+$", "", name)
            base = base.replace("_", " ").replace("-", " ").strip()
            if base:
                cleaned.append(base)
        return cleaned

    def _generate_options(
        self,
        query: str,
        contexts: list[RetrievedChunk],
        files: list[str],
    ) -> list[str]:
        # ファイルごとに代表スニペットを集約
        rep_by_file: dict[str, list[str]] = {}
        for item in contexts:
            name = item.file_name or ""
            if not name or name not in files:
                continue
            bucket = rep_by_file.setdefault(name, [])
            if len(bucket) < REP_CHUNKS_PER_FILE:
                bucket.append((item.snippet or item.text[:200]).strip())

        catalog_lines: list[str] = []
        for name in files[:MAX_OPTIONS]:
            snippets = rep_by_file.get(name, [])
            joined = " / ".join(snippets) if snippets else "(代表スニペットなし)"
            catalog_lines.append(f"- file: {name}\n  excerpt: {joined}")
        catalog = "\n".join(catalog_lines)

        system_prompt = (
            "あなたは藤花歯科クリニックの業務マニュアルナビゲーターです。\n"
            "ユーザーの質問が抽象的すぎて、複数の業務領域にまたがってしまっています。\n"
            "ユーザーが次に選びやすいよう、業務領域別の『具体的な質問例』を生成してください。\n"
            "\n"
            "出力ルール:\n"
            "- 各候補は15〜30字の短い質問形式（例：「保険会計の入力方法は？」）\n"
            "- 各業務領域から1つずつ、最大5個まで\n"
            "- 一般論ではなく、提示されたファイル内容に即した具体的な質問にする\n"
            "- 出力はJSON配列のみ（前後の説明文・コードブロック禁止）\n"
        )
        user_prompt = (
            f"ユーザーの質問: {query}\n\n"
            f"検索結果がまたがっている業務領域:\n{catalog}\n\n"
            'JSON形式の例: ["保険会計の入力方法は？", "自費会計の返金処理は？"]'
        )

        try:
            raw = self._gemini_client.generate_content(self._model, system_prompt, user_prompt)
        except GeminiApiError as exc:
            raise RuntimeError(str(exc)) from exc

        return self._parse_options(raw)

    def _parse_options(self, raw: str) -> list[str]:
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
            stripped = re.sub(r"```$", "", stripped).strip()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            logger.warning("Failed to parse clarification JSON: %s", stripped[:200])
            return []

        if not isinstance(parsed, list):
            return []

        options: list[str] = []
        for item in parsed:
            text = str(item).strip()
            if text and text not in options:
                options.append(text)
        return options
