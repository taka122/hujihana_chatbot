import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from math import sqrt
from typing import Dict, List, Protocol

from care_rag_poc.models import Facility, QueryIntent, ScoredFacility
from care_rag_poc.rag_types import RagGeneration


class GeminiApiError(RuntimeError):
    pass


class RagApiClient(Protocol):
    def embed_documents(self, texts: List[str], titles: List[str]) -> List[List[float]]:
        ...

    def embed_query(self, query: str) -> List[float]:
        ...

    def generate_content(self, system_instruction: str, user_prompt: str) -> str:
        ...


class GeminiApiClient:
    def __init__(
        self,
        api_key: str,
        generation_model: str = "gemini-2.0-flash",
        embedding_model: str = "gemini-embedding-001",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_sec: int = 30,
    ) -> None:
        self._api_key = api_key
        self._generation_model = generation_model
        self._embedding_model = embedding_model
        self._base_url = base_url.rstrip("/")
        self._timeout_sec = timeout_sec

    def embed_documents(self, texts: List[str], titles: List[str]) -> List[List[float]]:
        if len(texts) != len(titles):
            raise ValueError("texts and titles must have the same length")
        if not texts:
            return []

        requests = []
        for text, title in zip(texts, titles):
            requests.append(
                {
                    "model": f"models/{self._embedding_model}",
                    "taskType": "RETRIEVAL_DOCUMENT",
                    "title": title,
                    "content": {"parts": [{"text": text}]},
                }
            )

        payload = {"requests": requests}
        response = self._post(
            f"models/{self._embedding_model}:batchEmbedContents",
            payload,
        )
        embeddings = response.get("embeddings", [])
        if len(embeddings) != len(texts):
            raise GeminiApiError(
                f"Unexpected embedding count: expected {len(texts)}, got {len(embeddings)}"
            )
        return [item.get("values", []) for item in embeddings]

    def embed_query(self, query: str) -> List[float]:
        payload = {
            "model": f"models/{self._embedding_model}",
            "taskType": "RETRIEVAL_QUERY",
            "content": {"parts": [{"text": query}]},
        }
        response = self._post(
            f"models/{self._embedding_model}:embedContent",
            payload,
        )
        vector = response.get("embedding", {}).get("values", [])
        if not vector:
            raise GeminiApiError("Gemini returned an empty query embedding")
        return vector

    def generate_content(self, system_instruction: str, user_prompt: str) -> str:
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        response = self._post(
            f"models/{self._generation_model}:generateContent",
            payload,
        )
        candidates = response.get("candidates", [])
        for candidate in candidates:
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if text and text.strip():
                    return text.strip()
        raise GeminiApiError("Gemini returned no text candidates")

    def _post(self, path: str, payload: Dict) -> Dict:
        url = f"{self._base_url}/{path}"
        request = urllib.request.Request(
            url=url,
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_sec) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise GeminiApiError(f"Gemini API HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise GeminiApiError(f"Gemini API connection error: {exc}") from exc

        parsed = json.loads(raw)
        if "error" in parsed:
            raise GeminiApiError(str(parsed["error"]))
        return parsed


@dataclass
class _VectorDoc:
    facility: Facility
    text: str
    vector: List[float]


class FacilityRagResponder:
    def __init__(self, facilities: List[Facility], api_client: RagApiClient) -> None:
        self._api_client = api_client
        self._docs = self._build_docs(facilities)

    def _build_docs(self, facilities: List[Facility]) -> List[_VectorDoc]:
        if not facilities:
            return []
        texts = [self._render_doc(facility) for facility in facilities]
        titles = [facility.name for facility in facilities]
        vectors = self._api_client.embed_documents(texts=texts, titles=titles)
        return [
            _VectorDoc(facility=facility, text=text, vector=vector)
            for facility, text, vector in zip(facilities, texts, vectors)
        ]

    def generate(
        self,
        query: str,
        intent: QueryIntent,
        base_candidates: List[ScoredFacility],
        top_k: int,
    ) -> RagGeneration:
        semantic_candidates = self._semantic_retrieve(query, top_k=max(top_k, 3))
        merged_candidates = self._merge_candidates(
            base_candidates=base_candidates,
            semantic_candidates=semantic_candidates,
            top_k=top_k,
        )
        if not merged_candidates:
            return RagGeneration(
                text="該当候補を十分な根拠で提示できませんでした（不明）。",
                candidates=[],
            )

        context = self._build_context(merged_candidates)
        system_instruction = (
            "あなたは介護事業所案内アシスタントです。"
            "与えられた参照データだけを根拠に日本語で回答してください。"
            "根拠不十分な情報は推測せず『不明』と明記してください。"
            "医療・介護の最終判断は利用者と事業所に委ねる旨を短く添えてください。"
        )
        user_prompt = (
            f"相談内容:\n{query}\n\n"
            f"抽出条件:\n"
            f"- 都道府県: {intent.prefecture or '不明'}\n"
            f"- 市区: {intent.city or '不明'}\n"
            f"- サービス種別: {intent.service_type or '不明'}\n"
            f"- キーワード: {', '.join(intent.keywords) if intent.keywords else 'なし'}\n"
            f"- 連絡先表示希望: {'はい' if intent.contact_requested else 'いいえ'}\n\n"
            f"参照データ:\n{context}\n\n"
            "回答要件:\n"
            "- 候補は最大3件\n"
            "- 各候補に『理由』を1行つける\n"
            "- 各候補に根拠IDを [ID:xxxx] 形式でつける\n"
            "- 情報不足なら不明と書く\n"
        )

        answer = self._api_client.generate_content(system_instruction, user_prompt)
        return RagGeneration(text=answer, candidates=merged_candidates)

    def _semantic_retrieve(self, query: str, top_k: int) -> List[ScoredFacility]:
        if not self._docs:
            return []
        query_vector = self._api_client.embed_query(query)
        scored: List[ScoredFacility] = []
        for doc in self._docs:
            similarity = _cosine_similarity(query_vector, doc.vector)
            scored.append(
                ScoredFacility(
                    facility=doc.facility,
                    score=similarity,
                    reasons=[f"意味類似: {similarity:.3f}"],
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    @staticmethod
    def _merge_candidates(
        base_candidates: List[ScoredFacility],
        semantic_candidates: List[ScoredFacility],
        top_k: int,
    ) -> List[ScoredFacility]:
        merged: Dict[str, ScoredFacility] = {}

        for candidate in semantic_candidates:
            weighted = candidate.score * 5.0
            merged[candidate.facility.facility_id] = ScoredFacility(
                facility=candidate.facility,
                score=weighted,
                reasons=list(candidate.reasons),
            )

        for candidate in base_candidates:
            key = candidate.facility.facility_id
            if key in merged:
                current = merged[key]
                reasons = list(dict.fromkeys(current.reasons + candidate.reasons))
                merged[key] = ScoredFacility(
                    facility=current.facility,
                    score=current.score + candidate.score,
                    reasons=reasons,
                )
            else:
                merged[key] = ScoredFacility(
                    facility=candidate.facility,
                    score=candidate.score,
                    reasons=list(candidate.reasons),
                )

        items = list(merged.values())
        items.sort(key=lambda item: item.score, reverse=True)
        return items[:top_k]

    def _build_context(self, candidates: List[ScoredFacility]) -> str:
        blocks = []
        for candidate in candidates:
            facility = candidate.facility
            blocks.append(self._render_doc(facility))
        return "\n\n".join(blocks)

    @staticmethod
    def _render_doc(facility: Facility) -> str:
        return (
            f"[ID:{facility.facility_id}]\n"
            f"名称: {facility.name}\n"
            f"サービス: {facility.service_type}\n"
            f"地域: {facility.prefecture}{facility.city}\n"
            f"住所: {facility.address}\n"
            f"営業時間: {facility.business_hours}\n"
            f"特徴: {', '.join(facility.features)}\n"
            f"連絡先: {facility.phone}\n"
            f"更新日: {facility.last_updated}\n"
            f"ソース: {facility.source_url}"
        )


def build_gemini_rag_responder(
    facilities: List[Facility],
    api_key: str,
    generation_model: str = "gemini-2.0-flash",
    embedding_model: str = "gemini-embedding-001",
    timeout_sec: int = 30,
) -> FacilityRagResponder:
    api_client = GeminiApiClient(
        api_key=api_key,
        generation_model=generation_model,
        embedding_model=embedding_model,
        timeout_sec=timeout_sec,
    )
    return FacilityRagResponder(facilities=facilities, api_client=api_client)


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(l * r for l, r in zip(left, right))
    left_norm = sqrt(sum(l * l for l in left))
    right_norm = sqrt(sum(r * r for r in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)

