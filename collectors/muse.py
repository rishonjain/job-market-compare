"""The Muse public API: https://www.themuse.com/developers/api/v2 — keyless, mostly US employers."""
import time
from datetime import datetime, timedelta, timezone

from collectors.http import session
from collectors.relevant import is_relevant
from config import CURRENCY

COUNTRIES = ["us", "ca", "au", "nz", "ie", "nl", "de", "se", "it", "fr", "hk", "dk", "no", "fi", "ae", "sg", "my", "vn"]
URL = "https://www.themuse.com/api/public/jobs"
CATEGORIES = ["Data and Analytics", "Software Engineering"]  # ML/AI engineers often sit in the latter
MAX_PAGES = 60  # keyless limit is 500 requests/hour
NAMES = {
    "Canada": "ca", "Australia": "au", "New Zealand": "nz", "Ireland": "ie", "Netherlands": "nl", "Germany": "de",
    "Sweden": "se", "Italy": "it", "France": "fr", "Hong Kong": "hk", "Denmark": "dk", "Norway": "no",
    "Finland": "fi", "United Arab Emirates": "ae", "Singapore": "sg", "Malaysia": "my", "Vietnam": "vn",
}
_http = session()


def country_of(location):
    tail = location.split(", ")[-1]
    # shortcut: "City, XX" is read as a US state; fine as Muse spells other countries out.
    return "us" if len(tail) == 2 and tail.isupper() else NAMES.get(tail)


def collect_all(days):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    for cat in CATEGORIES:
        for page in range(1, MAX_PAGES + 1):
            r = _http.get(URL, params={"page": page, "category": cat}, timeout=30)
            r.raise_for_status()
            data = r.json()
            for j in data["results"]:
                country = next(filter(None, (country_of(l["name"]) for l in j["locations"])), None)
                posted = datetime.fromisoformat(j["publication_date"])
                if country and posted >= since and is_relevant(j["name"]):
                    yield to_row(j, country)
            if page >= data["page_count"]:
                break
            time.sleep(0.5)


def to_row(j, country):
    locs = [l["name"] for l in j["locations"]]
    return {
        "source": "muse", "source_id": str(j["id"]), "country": country, "search_term": None,
        "title": j["name"], "company": (j.get("company") or {}).get("name"),
        "location": next((l for l in locs if country_of(l) == country), None), "region": None,
        "description": j.get("contents"),  # HTML
        "salary_min": None, "salary_max": None, "salary_currency": CURRENCY[country],
        "salary_period": None, "salary_text": None,
        "contract_type": None, "posted_at": j["publication_date"],
        "url": (j.get("refs") or {}).get("landing_page"), "raw": j,  # raw["levels"] holds Muse's entry/senior tag
    }
