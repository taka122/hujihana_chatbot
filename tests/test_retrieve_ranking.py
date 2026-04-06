import unittest

from app.services.retrieve import _query_alignment_bonus


class RetrieveRankingTest(unittest.TestCase):
    def test_title_match_gets_bonus(self) -> None:
        bonus = _query_alignment_bonus(
            query="朝の準備の流れを教えて",
            file_name="朝の準備.pdf",
            section_title=None,
            snippet="受付開始前に確認する項目です。",
        )
        self.assertGreater(bonus, 0.0)

    def test_unrelated_title_gets_no_bonus(self) -> None:
        bonus = _query_alignment_bonus(
            query="マイナンバー確認の流れ",
            file_name="朝の準備.pdf",
            section_title=None,
            snippet="受付開始前に確認する項目です。",
        )
        self.assertEqual(bonus, 0.0)


if __name__ == "__main__":
    unittest.main()
