import unittest
import sys
import types
from types import SimpleNamespace
from unittest.mock import patch

if "docx" not in sys.modules:
    fake_docx = types.ModuleType("docx")
    fake_docx.Document = object
    sys.modules["docx"] = fake_docx

if "pypdf" not in sys.modules:
    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = object
    sys.modules["pypdf"] = fake_pypdf

from app.services.ingest import _parse_pdf


class FakePage:
    def __init__(self, text: str) -> None:
        self._text = text
        self.images = []

    def extract_text(self) -> str:
        return self._text


class FakeReader:
    def __init__(self, pages):
        self.pages = pages


def build_settings(**overrides):
    defaults = {
        "pdf_min_text_chars_per_page": 40,
        "image_only_pdf_ratio_threshold": 0.9,
        "pdf_ocr_enabled": True,
        "pdf_ocr_model": "gemini-2.0-flash",
        "pdf_ocr_max_pages_per_doc": 20,
        "gemini_api_key": None,
        "gemini_base_url": "https://example.invalid",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class ParsePdfTest(unittest.TestCase):
    def run_parse(self, pages, settings, ocr_by_page=None):
        ocr_text_by_id = {id(page): text for page, text in (ocr_by_page or {}).items()}

        def fake_ocr(page, _client, _model):
            return ocr_text_by_id.get(id(page), "")

        with (
            patch("app.services.ingest.get_settings", return_value=settings),
            patch("app.services.ingest.PdfReader", return_value=FakeReader(pages)),
            patch("app.services.ingest.GeminiClient", return_value=object()),
            patch("app.services.ingest._extract_page_text_via_ocr", side_effect=fake_ocr),
        ):
            return _parse_pdf(b"%PDF-1.4")

    def test_short_text_page_is_included(self) -> None:
        pages = [
            FakePage("A" * 100),
            FakePage("抜歯鉗子 / エレベーター / 滅菌ガーゼ / 止血材"),
        ]
        result = self.run_parse(pages, settings=build_settings(gemini_api_key=None))

        self.assertEqual(result.extracted_pages, 2)
        self.assertEqual(result.failed_pages, [])
        self.assertEqual(result.ocr_used_pages, [])
        self.assertIn("SHORT_TEXT_INCLUDED", result.tags)
        self.assertEqual([block.page for block in result.blocks], [1, 2])

    def test_empty_text_page_is_still_failed(self) -> None:
        pages = [
            FakePage("A" * 100),
            FakePage("   "),
        ]
        result = self.run_parse(pages, settings=build_settings(gemini_api_key=None))

        self.assertEqual(result.extracted_pages, 1)
        self.assertEqual(result.failed_pages, [{"page": 2, "reason": "image_only_or_no_text"}])
        self.assertEqual(result.ocr_used_pages, [])

    def test_short_ocr_text_is_used_when_raw_text_empty(self) -> None:
        pages = [
            FakePage("A" * 100),
            FakePage(""),
        ]
        result = self.run_parse(
            pages,
            settings=build_settings(gemini_api_key="dummy-key"),
            ocr_by_page={pages[1]: "注意事項"},
        )

        self.assertEqual(result.extracted_pages, 2)
        self.assertEqual(result.failed_pages, [])
        self.assertEqual(result.ocr_used_pages, [2])
        self.assertIn("SHORT_TEXT_INCLUDED", result.tags)
        self.assertIn("OCR_USED", result.tags)
        self.assertEqual(result.blocks[1].text, "注意事項")


if __name__ == "__main__":
    unittest.main()
