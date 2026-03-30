import csv
from pathlib import Path
from typing import List

from care_rag_poc.models import Facility


def _split_features(raw: str) -> List[str]:
    return [item.strip() for item in raw.split("|") if item.strip()]


def load_facilities(csv_path: str) -> List[Facility]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    facilities: List[Facility] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            facilities.append(
                Facility(
                    facility_id=row["id"].strip(),
                    name=row["name"].strip(),
                    prefecture=row["prefecture"].strip(),
                    city=row["city"].strip(),
                    service_type=row["service_type"].strip(),
                    address=row["address"].strip(),
                    phone=row["phone"].strip(),
                    business_hours=row["business_hours"].strip(),
                    features=_split_features(row["features"]),
                    last_updated=row["last_updated"].strip(),
                    source_url=row["source_url"].strip(),
                )
            )

    if not facilities:
        raise ValueError(f"No facility records in CSV: {path}")
    return facilities

