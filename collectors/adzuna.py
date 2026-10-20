"""Adzuna API: https://developer.adzuna.com — free key, 8 of our 11 countries."""
import os
import time

from collectors.http import session
from config import CURRENCY

COUNTRIES = ["us", "ca", "au", "nz", "nl", "de", "it", "fr", "sg"]
URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
PER_PAGE = 50
_http = session()


def collect(country, term, days, max_pages=20):
    params = {
        "app_id": os.environ["ADZUNA_APP_ID"], "app_key": os.environ["ADZUNA_APP_KEY"],
        "results_per_page": PER_PAGE, "title_only": term, "max_days_old": days,
    }
    for page in range(1, max_pages + 1):
        r = _http.get(URL.format(country=country, page=page), params=params, timeout=30)
        r.raise_for_status()
        results = r.json()["results"]
        for j in results:
            yield to_row(j, country, term)
        time.sleep(2.5)  # free tier allows 25 requests/minute
        if len(results) < PER_PAGE:
            break


def to_row(j, country, term):
    loc = j.get("location") or {}
    area = loc.get("area") or []
    # Adzuna fills missing salaries with its own model estimate; that's not real data, so drop it (raw keeps it).
    real_salary = str(j.get("salary_is_predicted", "0")) == "0"
    return {
        "source": "adzuna", "source_id": str(j["id"]), "country": country, "search_term": term,
        "title": j.get("title"), "company": (j.get("company") or {}).get("display_name"),
        "location": loc.get("display_name"), "region": area[1] if len(area) > 1 else None,
        "description": j.get("description"),  # Adzuna truncates this to ~500 chars
        "salary_min": j.get("salary_min") if real_salary else None,
        "salary_max": j.get("salary_max") if real_salary else None,
        "salary_currency": CURRENCY[country], "salary_period": "year", "salary_text": None,
        "contract_type": " ".join(filter(None, [j.get("contract_time"), j.get("contract_type")])) or None,
        "posted_at": j.get("created"), "url": j.get("redirect_url"), "raw": j,
    }
