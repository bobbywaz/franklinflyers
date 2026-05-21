import datetime
import re
from typing import Dict, List, Optional, Sequence, Tuple

def extract_deals_from_overlay_labels(labels: Sequence[str]) -> List[Dict]:
    deals: List[Dict] = []
    seen = set()

    for label in labels:
        deal = parse_overlay_label(label)
        if not deal:
            continue
        key = (deal["name"].lower(), deal["price"].lower(), deal["description"].lower())
        if key in seen:
            continue
        seen.add(key)
        deals.append(deal)

    return deals

def parse_overlay_label(label: str) -> Optional[Dict]:
    cleaned = re.sub(r"\s+", " ", label).strip()
    cleaned = cleaned.replace(" . Select for details.", "").replace(". Select for details.", "")
    cleaned = cleaned.strip(" .")
    if not cleaned or "Select for details" not in label:
        return None

    parts = [part.strip(" .") for part in cleaned.split(",")]
    if not parts:
        return None

    name = parts[0].strip()
    remainder = [part for part in parts[1:] if part]
    if not name or not remainder:
        return None

    price = remainder[-1]
    description = ", ".join(remainder[:-1]).strip()
    return {
        "name": name,
        "price": price,
        "description": description,
    }

def extract_flyer_dates(main_text: str) -> Tuple[Optional[datetime.date], Optional[datetime.date]]:
    match = re.search(
        r"([A-Za-z]{3,9}\s+\d{1,2})(?:st|nd|rd|th)?\s*-\s*([A-Za-z]{3,9}\s+\d{1,2})(?:st|nd|rd|th)?",
        main_text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, None

    current_year = datetime.date.today().year
    try:
        start = datetime.datetime.strptime(f"{match.group(1)} {current_year}", "%b %d %Y").date()
    except ValueError:
        start = datetime.datetime.strptime(f"{match.group(1)} {current_year}", "%B %d %Y").date()

    try:
        end = datetime.datetime.strptime(f"{match.group(2)} {current_year}", "%b %d %Y").date()
    except ValueError:
        end = datetime.datetime.strptime(f"{match.group(2)} {current_year}", "%B %d %Y").date()

    if end < start:
        end = end.replace(year=end.year + 1)
    return start, end
