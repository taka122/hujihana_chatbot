import unittest

from care_rag_poc.chat_engine import CareRagChatEngine
from care_rag_poc.dataset import load_facilities
from care_rag_poc.retriever import FacilityRetriever


class ChatEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        facilities = load_facilities("data/facilities_sample.csv")
        self.engine = CareRagChatEngine(FacilityRetriever(facilities))

    def test_returns_candidates_for_city_and_service(self) -> None:
        result = self.engine.ask("世田谷区でデイサービスを探しています")
        self.assertGreaterEqual(len(result.candidates), 1)
        self.assertIn("世田谷区", result.text)
        self.assertIn("デイサービス", result.text)

    def test_asks_for_clarification_when_query_is_too_vague(self) -> None:
        result = self.engine.ask("おすすめありますか")
        self.assertEqual(len(result.candidates), 0)
        self.assertIn("条件が不足", result.text)

    def test_returns_unknown_when_no_strong_match(self) -> None:
        result = self.engine.ask("沖縄県で夜間の小規模多機能を探しています")
        self.assertEqual(len(result.candidates), 0)
        self.assertIn("不明", result.text)


if __name__ == "__main__":
    unittest.main()
