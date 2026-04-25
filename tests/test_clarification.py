"""ClarificationService の単体テスト。

LLM 呼び出しはモック化し、判定ロジック（散らばり度）と候補パースを検証する。
"""

from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from app.services.clarification import (
    SCATTER_THRESHOLD,
    ClarificationResult,
    ClarificationService,
)
from app.services.retrieve import RetrievedChunk


def _make_chunk(file_name: str, score: float = 0.9) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        file_name=file_name,
        ref_type="page",
        ref="p.1",
        snippet=f"{file_name} の代表スニペット",
        text=f"{file_name} の本文テキスト" * 10,
        page_start=1,
        page_end=1,
        section_title=None,
        score=score,
        raw_score=score,
    )


def _make_service() -> ClarificationService:
    """GEMINI_API_KEY が必須なので、ダミー値で初期化する。"""
    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "test-dummy-key"},
        clear=False,
    ):
        return ClarificationService(gemini_api_key="test-dummy-key")


class ClarificationServiceTest(unittest.TestCase):
    def test_returns_not_needed_when_contexts_are_empty(self) -> None:
        service = _make_service()
        result = service.evaluate(query="会計", contexts=[])
        self.assertFalse(result.needed)
        self.assertEqual(result.options, [])

    def test_returns_not_needed_when_results_are_concentrated_in_few_files(self) -> None:
        # 2ファイルに集中 → 曖昧ではない（しきい値は3）
        service = _make_service()
        contexts = [
            _make_chunk("受付マニュアル.pdf"),
            _make_chunk("受付マニュアル.pdf"),
            _make_chunk("会計マニュアル.pdf"),
        ]
        result = service.evaluate(query="保険会計", contexts=contexts)
        self.assertFalse(result.needed)

    def test_returns_clarification_when_results_scatter_across_threshold_files(self) -> None:
        # しきい値以上のファイルにまたがる → 曖昧
        service = _make_service()
        contexts = [
            _make_chunk("受付マニュアル.pdf"),
            _make_chunk("会計マニュアル.pdf"),
            _make_chunk("予約管理マニュアル.pdf"),
            _make_chunk("ヒヤリハットマニュアル.pdf"),
        ]
        # LLM 呼び出しをモック化して、決まった候補を返す
        with patch.object(
            ClarificationService,
            "_generate_options",
            return_value=[
                "受付の流れは？",
                "会計入力の手順は？",
                "予約変更の方法は？",
                "ヒヤリハット報告のテンプレは？",
            ],
        ):
            result = service.evaluate(query="業務", contexts=contexts)

        self.assertTrue(result.needed)
        self.assertIn("業務", result.question)
        self.assertGreaterEqual(len(result.options), SCATTER_THRESHOLD)

    def test_falls_back_to_filenames_when_llm_fails(self) -> None:
        # LLM が例外を投げたら、ファイル名のフォールバックを使う
        service = _make_service()
        contexts = [
            _make_chunk("受付マニュアル.pdf"),
            _make_chunk("会計マニュアル.pdf"),
            _make_chunk("予約管理マニュアル.pdf"),
        ]
        with patch.object(
            ClarificationService,
            "_generate_options",
            side_effect=RuntimeError("LLM down"),
        ):
            result = service.evaluate(query="業務", contexts=contexts)

        self.assertTrue(result.needed)
        # ファイル名から拡張子が落ちて、人間可読な名前になっていること
        self.assertTrue(any("受付マニュアル" in opt for opt in result.options))
        self.assertTrue(any("会計マニュアル" in opt for opt in result.options))
        # 拡張子は除去されている
        for opt in result.options:
            self.assertFalse(opt.endswith(".pdf"))

    def test_parse_options_handles_code_block_wrapped_json(self) -> None:
        service = _make_service()
        raw = '```json\n["保険会計の入力方法は？", "返金処理の手順は？"]\n```'
        options = service._parse_options(raw)
        self.assertEqual(options, ["保険会計の入力方法は？", "返金処理の手順は？"])

    def test_parse_options_returns_empty_for_invalid_json(self) -> None:
        service = _make_service()
        options = service._parse_options("not json at all")
        self.assertEqual(options, [])

    def test_parse_options_dedupes(self) -> None:
        service = _make_service()
        raw = '["保険会計", "保険会計", "返金処理"]'
        options = service._parse_options(raw)
        self.assertEqual(options, ["保険会計", "返金処理"])


class ClarificationResultTest(unittest.TestCase):
    def test_dataclass_default_shape(self) -> None:
        result = ClarificationResult(needed=False, question="", options=[])
        self.assertFalse(result.needed)
        self.assertEqual(result.options, [])


if __name__ == "__main__":
    unittest.main()
