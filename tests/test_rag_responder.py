import unittest

from care_rag_poc.chat_engine import CareRagChatEngine
from care_rag_poc.dataset import load_facilities
from care_rag_poc.rag import FacilityRagResponder
from care_rag_poc.retriever import FacilityRetriever


class FakeGeminiClient:
    def embed_documents(self, texts, titles):
        return [self._vectorize(text) for text in texts]

    def embed_query(self, query):
        return self._vectorize(query)

    def generate_content(self, system_instruction, user_prompt):
        return "生成回答: 参照データに基づいて候補を提示します。"

    @staticmethod
    def _vectorize(text):
        keys = ["世田谷区", "杉並区", "デイサービス", "訪問介護", "認知症", "送迎"]
        vector = [1.0 if key in text else 0.0 for key in keys]
        if sum(vector) == 0:
            return [0.1 for _ in keys]
        return vector


class RagResponderTest(unittest.TestCase):
    def setUp(self):
        facilities = load_facilities("data/facilities_sample.csv")
        self.retriever = FacilityRetriever(facilities)
        self.responder = FacilityRagResponder(
            facilities=facilities,
            api_client=FakeGeminiClient(),
        )

    def test_generate_returns_llm_text_and_candidates(self):
        intent = self.retriever.parse_intent("世田谷区でデイサービスを探しています")
        base_candidates = self.retriever.retrieve(intent, top_k=2)
        result = self.responder.generate(
            query="世田谷区でデイサービスを探しています",
            intent=intent,
            base_candidates=base_candidates,
            top_k=2,
        )
        self.assertIn("生成回答", result.text)
        self.assertGreaterEqual(len(result.candidates), 1)

    def test_chat_engine_uses_rag_responder(self):
        engine = CareRagChatEngine(self.retriever, rag_responder=self.responder)
        result = engine.ask("世田谷区でデイサービスを探しています", top_k=2)
        self.assertIn("生成回答", result.text)
        self.assertGreaterEqual(len(result.candidates), 1)


if __name__ == "__main__":
    unittest.main()

