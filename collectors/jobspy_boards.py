"""Indeed, LinkedIn and Glassdoor through python-jobspy (scraping: small volumes, personal research only)."""
import json
import time

import pandas as pd
from jobspy import scrape_jobs

from config import CURRENCY, COUNTRIES as NAMES

COUNTRIES = list(NAMES)
LOCATION = {"ae": "Dubai", "hk": "Hong Kong"}
RESULTS = 50
# LinkedIn descriptions cost one extra request per job, so they stay off.
# shortcut: LinkedIn rows have no description, turn on linkedin_fetch_description if skills/visa need it.
BOARDS = ["indeed", "linkedin", "glassdoor"]
# Glassdoor only serves some countries; the rest just return nothing or error and are skipped.


def collect(country, term, days, max_pages=None):
    for board in BOARDS:
        try:
            df = scrape_jobs(
                site_name=board, search_term=term, location=LOCATION.get(country, NAMES[country]),
                country_indeed=NAMES[country] if country != "ae" else "united arab emirates",
                results_wanted=RESULTS, hours_old=days * 24, verbose=0,
            )
        except Exception as e:
            print(f"  {board} {country} '{term}': {e}")
            continue
        for rec in df.to_dict("records"):
            yield to_row(rec, board, country, term)
        time.sleep(3)


def to_row(j, board, country, term):
    j = {k: (None if pd.isna(v) else v) if not isinstance(v, (list, dict)) else v for k, v in j.items()}
    amount = lambda k: j.get(k)
    return {
        "source": board, "source_id": str(j["id"]), "country": country, "search_term": term,
        "title": j.get("title"), "company": j.get("company"),
        "location": j.get("location"), "region": None, "description": j.get("description"),
        "salary_min": amount("min_amount"), "salary_max": amount("max_amount"),
        "salary_currency": j.get("currency") or CURRENCY[country], "salary_period": j.get("interval"),
        "salary_text": None, "contract_type": j.get("job_type"),
        "posted_at": str(j["date_posted"]) if j.get("date_posted") else None,
        "url": j.get("job_url"), "raw": json.loads(json.dumps(j, default=str)),
    }
