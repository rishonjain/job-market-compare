"""Jooble partner API: https://jooble.org/api/about — free key, but only 500 requests total.

The key belongs to the US site (jooble.org): Ireland/Dubai searches return ~nothing, so US only.
Every request is counted in data/jooble_calls.txt and collection stops at the budget.
"""
import os
from datetime import datetime, timedelta, timezone

import db
from collectors.http import session

COUNTRIES = ["us"]
URL = "https://jooble.org/api/{key}"
PER_PAGE = 100
BUDGET = 500
CALLS = db.DB_PATH.parent / "jooble_calls.txt"
_http = session({"Content-Type": "application/json"})


def calls_used():
    return int(CALLS.read_text()) if CALLS.exists() else 0


def _count_call():
    CALLS.parent.mkdir(exist_ok=True)
    CALLS.write_text(str(calls_used() + 1))


def collect(country, term, days, max_pages=5):
    key = os.environ.get("JOOBLE_API_KEY")
    if not key:
        return
    since = datetime.now(timezone.utc) - timedelta(days=days)
    body = {"keywords": term, "location": "United States", "ResultOnPage": PER_PAGE,
            "datecreatedfrom": since.strftime("%Y-%m-%d")}
    for page in range(1, max_pages + 1):
        if calls_used() >= BUDGET:
            raise RuntimeError(f"Jooble budget of {BUDGET} calls used up")
        _count_call()
        r = _http.post(URL.format(key=key), json={**body, "page": page}, timeout=30)
        r.raise_for_status()
        jobs = r.json().get("jobs") or []
        for j in jobs:
            yield to_row(j, term)
        if len(jobs) < PER_PAGE:
            break


def to_row(j, term):
    return {
        "source": "jooble", "source_id": str(j["id"]), "country": "us", "search_term": term,
        "title": j.get("title"), "company": j.get("company") or None,
        "location": j.get("location"), "region": None,
        "description": j.get("snippet"),  # Jooble only gives a short snippet
        "salary_min": None, "salary_max": None, "salary_currency": "USD", "salary_period": None,
        "salary_text": j.get("salary") or None, "contract_type": j.get("type") or None,
        "posted_at": j.get("updated"), "url": j.get("link"), "raw": j,
    }
