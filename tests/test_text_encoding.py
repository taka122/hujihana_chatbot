import codecs
import unittest

from app.services.text_decode import decode_text_bytes, extract_charset_from_mime, is_probably_garbled_text


class TextEncodingTest(unittest.TestCase):
    def test_extract_charset_from_mime(self) -> None:
        charset = extract_charset_from_mime("text/plain; charset=Shift_JIS")
        self.assertEqual(charset, "shift_jis")

    def test_auto_detect_utf8_bom(self) -> None:
        raw = codecs.BOM_UTF8 + "こんにちは".encode("utf-8")
        decoded = decode_text_bytes(raw)
        self.assertEqual(decoded.text, "こんにちは")
        self.assertIn("utf-8", decoded.encoding)
        self.assertFalse(decoded.had_replacements)

    def test_auto_detect_cp932(self) -> None:
        original = "介護保険の自己負担割合"
        raw = original.encode("cp932")
        decoded = decode_text_bytes(raw)
        self.assertEqual(decoded.text, original)
        self.assertIn(decoded.encoding, {"cp932", "shift_jis"})
        self.assertFalse(decoded.had_replacements)

    def test_fallback_marks_replacement(self) -> None:
        decoded = decode_text_bytes(b"\x81")
        self.assertTrue(decoded.had_replacements)
        self.assertIn("DECODE_REPLACED", decoded.tags)

    def test_garbled_pdf_text_is_detected(self) -> None:
        garbled = "ʷɹɹɹܭ ͓௼Γમ 1BZ-JHIU ͨ͠΋ͷ͕ड෇ͷਅΜத"
        self.assertTrue(is_probably_garbled_text(garbled))

    def test_normal_japanese_text_is_not_flagged(self) -> None:
        normal = "朝の準備では、予約表と釣り銭を確認します。"
        self.assertFalse(is_probably_garbled_text(normal))

if __name__ == "__main__":
    unittest.main()
