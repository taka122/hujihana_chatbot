from typing import Dict, List, Optional, Set

from care_rag_poc.models import ConversationState, Facility, QueryIntent, ScoredFacility


DEFAULT_SERVICE_SYNONYMS: Dict[str, List[str]] = {
    "デイサービス": ["デイサービス", "通所介護", "通所サービス"],
    "訪問介護": ["訪問介護", "ホームヘルプ", "ヘルパー"],
    "ショートステイ": ["ショートステイ", "短期入所"],
    "グループホーム": ["グループホーム", "認知症対応型共同生活介護"],
    "有料老人ホーム": ["有料老人ホーム", "介護付き有料", "住宅型有料"],
    "居宅介護支援": ["居宅介護支援", "ケアマネ", "ケアマネジャー"],
}

FEATURE_KEYWORDS = {
    "認知症",
    "送迎",
    "入浴",
    "機能訓練",
    "リハビリ",
    "看護師",
    "医療連携",
    "夜間",
    "24時間",
    "土日",
    "短時間",
    "女性スタッフ",
    "男性スタッフ",
    "要支援",
    "要介護",
}

CONTACT_KEYWORDS = {"電話", "連絡先", "問い合わせ", "問合せ", "TEL"}


class FacilityRetriever:
    def __init__(self, facilities: List[Facility]) -> None:
        self._facilities = facilities
        self._cities = sorted({f.city for f in facilities}, key=len, reverse=True)
        self._prefectures = sorted({f.prefecture for f in facilities}, key=len, reverse=True)
        self._service_alias_to_canonical = self._build_service_aliases(facilities)

    def _build_service_aliases(self, facilities: List[Facility]) -> Dict[str, str]:
        alias_map: Dict[str, str] = {}
        for canonical, aliases in DEFAULT_SERVICE_SYNONYMS.items():
            for alias in aliases + [canonical]:
                alias_map[alias] = canonical

        for facility in facilities:
            alias_map.setdefault(facility.service_type, facility.service_type)
        return alias_map

    def parse_intent(self, query: str, state: Optional[ConversationState] = None) -> QueryIntent:
        prefecture = self._find_first_match(query, self._prefectures)
        city = self._find_first_match(query, self._cities)
        service_type = self._find_service_type(query)
        keywords = sorted([kw for kw in FEATURE_KEYWORDS if kw in query])
        contact_requested = any(kw in query for kw in CONTACT_KEYWORDS)

        if state:
            if not prefecture:
                prefecture = state.prefecture
            if not city:
                city = state.city
            if not service_type:
                service_type = state.service_type
            merged = set(state.keywords)
            merged.update(keywords)
            keywords = sorted(merged)

        return QueryIntent(
            raw_query=query,
            prefecture=prefecture,
            city=city,
            service_type=service_type,
            keywords=keywords,
            contact_requested=contact_requested,
        )

    def retrieve(self, intent: QueryIntent, top_k: int = 3) -> List[ScoredFacility]:
        candidates = self._facilities
        if intent.city:
            city_matched = [f for f in candidates if f.city == intent.city]
            if city_matched:
                candidates = city_matched
        if intent.service_type:
            service_matched = [f for f in candidates if f.service_type == intent.service_type]
            if service_matched:
                candidates = service_matched

        scored: List[ScoredFacility] = []
        for facility in candidates:
            score = 0.0
            reasons: List[str] = []
            blob = facility.search_blob

            if intent.prefecture and facility.prefecture == intent.prefecture:
                score += 1.0
                reasons.append(f"地域一致: {facility.prefecture}")
            if intent.city and facility.city == intent.city:
                score += 3.0
                reasons.append(f"市区一致: {facility.city}")
            if intent.service_type and facility.service_type == intent.service_type:
                score += 4.0
                reasons.append(f"サービス一致: {facility.service_type}")
            if facility.name in intent.raw_query:
                score += 2.0
                reasons.append("事業所名一致")

            for keyword in intent.keywords:
                if keyword in blob:
                    score += 1.2
                    reasons.append(f"条件一致: {keyword}")

            if not reasons and any(fragment in blob for fragment in self._soft_fragments(intent.raw_query)):
                score += 0.5
                reasons.append("部分一致")

            scored.append(ScoredFacility(facility=facility, score=score, reasons=reasons))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def _find_service_type(self, query: str) -> Optional[str]:
        longest_alias = self._find_first_match(query, sorted(self._service_alias_to_canonical.keys(), key=len, reverse=True))
        if not longest_alias:
            return None
        return self._service_alias_to_canonical[longest_alias]

    @staticmethod
    def _find_first_match(text: str, candidates: List[str]) -> Optional[str]:
        for candidate in candidates:
            if candidate and candidate in text:
                return candidate
        return None

    @staticmethod
    def _soft_fragments(text: str) -> Set[str]:
        cleaned = (
            text.replace("。", " ")
            .replace("、", " ")
            .replace("？", " ")
            .replace("?", " ")
            .replace("！", " ")
            .replace("!", " ")
        )
        return {token for token in cleaned.split() if len(token) >= 2}

