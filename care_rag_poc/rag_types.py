from dataclasses import dataclass
from typing import List, Protocol

from care_rag_poc.models import QueryIntent, ScoredFacility


@dataclass
class RagGeneration:
    text: str
    candidates: List[ScoredFacility]


class RagResponder(Protocol):
    def generate(
        self,
        query: str,
        intent: QueryIntent,
        base_candidates: List[ScoredFacility],
        top_k: int,
    ) -> RagGeneration:
        ...

