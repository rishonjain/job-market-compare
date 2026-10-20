"""Swedish Public Employment Service open API: https://jobsearch.api.jobtechdev.se — no key needed."""
from datetime import datetime, timedelta, timezone

from collectors.http import session

COUNTRIES = ["se"]
URL = "https://jobsearch.api.jobtechdev.se/search"
PER_PAGE = 100
MAX_OFFSET = 2000  # API rejects offsets beyond this
_http = session()


def collect(country, term, days, max_pages=None):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    for offset in range(0, MAX_OFFSET + 1, PER_PAGE):
        # quoted = phrase match; unquoted matches any single word
        params = {"q": f'"{term}"', "limit": PER_PAGE, "offset": offset, "published-after": since}
        r = _http.get(URL, params=params, timeout=30)
        r.raise_for_status()
        hits = r.json()["hits"]
        for j in hits:
            yield to_row(j, term)
        if len(hits) < PER_PAGE:
            break


def to_row(j, term):
    addr = j.get("workplace_address") or {}
    label = lambda k: (j.get(k) or {}).get("label")
    return {
        "source": "jobtech", "source_id": str(j["id"]), "country": "se", "search_term": term,
        "title": j.get("headline"), "company": (j.get("employer") or {}).get("name"),
        "location": addr.get("municipality") or addr.get("city"), "region": addr.get("region"),
        "description": (j.get("description") or {}).get("text"),
        "salary_min": None, "salary_max": None, "salary_currency": "SEK",
        "salary_period": None, "salary_text": " | ".join(filter(None, [label("salary_type"), j.get("salary_description")])) or None,
        "contract_type": " ".join(filter(None, [label("working_hours_type"), label("employment_type")])) or None,
        "posted_at": j.get("publication_date"), "url": j.get("webpage_url"), "raw": j,
    }
