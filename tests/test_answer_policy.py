import unittest
import uuid

from app.services.answer import AnswerService
from app.services.retrieve import RetrievedChunk


class FakeGeminiClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def generate_content(self, model: str, system_prompt: str, user_prompt: str, file_uri=None, mime_type=None) -> str:
        self.calls.append(
            {
                "model": model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        return (
            '{"answer":{"conclusion":"ok","details":"完全な手順","notes":"","next_actions":[]},'
            f'"citations":[{{"chunk_id":"{self.calls and self.calls[0] and self._chunk_id}"}}]}}'
        )

    _chunk_id: str = ""


class AnswerPolicyTest(unittest.TestCase):
    def test_generate_gemini_prompt_requests_exhaustive_merged_answer(self) -> None:
        chunk_id = uuid.uuid4()
        fake_client = FakeGeminiClient()
        fake_client._chunk_id = str(chunk_id)

        service = AnswerService.__new__(AnswerService)
        service._model = "gemini-2.0-flash"
        service._gemini_client = fake_client

        context = RetrievedChunk(
            chunk_id=chunk_id,
            document_id=uuid.uuid4(),
            file_name="本人確認マニュアル.pdf",
            ref_type="page",
            ref="p.2",
            snippet="本人確認の手順を説明",
            text="1. 書類を確認する 2. 氏名と住所を照合する",
            page_start=2,
            page_end=2,
            section_title=None,
            score=0.91,
            raw_score=0.91,
            storage_key="workspaces/test/documents/manual.pdf",
        )

        raw = service._generate_gemini("本人確認の流れを教えて", [context])

        self.assertIn("すべての資料断片を漏れなく確認", fake_client.calls[0]["system_prompt"])
        self.assertIn("details は参照資料を統合した完全版の手順・要点説明にする", fake_client.calls[0]["user_prompt"])
        self.assertIn(str(chunk_id), raw)


if __name__ == "__main__":
    unittest.main()
