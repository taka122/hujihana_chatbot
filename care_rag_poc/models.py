from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Facility:
    facility_id: str
    name: str
    prefecture: str
    city: str
    service_type: str
    address: str
    phone: str
    business_hours: str
    features: List[str]
    last_updated: str
    source_url: str

    @property
    def search_blob(self) -> str:
        return " ".join(
            [
                self.name,
                self.prefecture,
                self.city,
                self.service_type,
                self.address,
                self.business_hours,
                *self.features,
            ]
        )


@dataclass
class QueryIntent:
    raw_query: str
    prefecture: Optional[str] = None
    city: Optional[str] = None
    service_type: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    contact_requested: bool = False


@dataclass
class ScoredFacility:
    facility: Facility
    score: float
    reasons: List[str]


@dataclass
class ConversationState:
    prefecture: Optional[str] = None
    city: Optional[str] = None
    service_type: Optional[str] = None
    keywords: List[str] = field(default_factory=list)


@dataclass
class ChatResult:
    text: str
    intent: QueryIntent
    candidates: List[ScoredFacility]

