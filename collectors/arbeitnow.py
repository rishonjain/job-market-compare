"""Arbeitnow free job-board API: https://www.arbeitnow.com/blog/job-board-api — keyless, newest first, DACH/EU-wide."""
import time
from datetime import datetime, timedelta, timezone

from collectors.http import session
from collectors.relevant import is_relevant
from config import CURRENCY

COUNTRIES = ["de", "nl", "fr", "se", "dk", "no", "fi", "ie", "it"]
URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 30
# Feed mixes countries and gives only a free-text location; match country names and major cities.
PLACES = {
    "de": ["germany", "deutschland", "berlin", "munich", "münchen", "hamburg", "cologne", "köln", "frankfurt", "stuttgart",
           "düsseldorf", "nuremberg", "leipzig", "dresden", "hannover", "bayern", "karlsruhe", "bochum", "bremen"],
    "nl": ["netherlands", "nederland", "amsterdam", "rotterdam", "den haag", "the hague", "utrecht", "eindhoven", "delft"],
    "fr": ["france", "paris", "lyon", "bordeaux", "toulouse", "marseille", "nantes", "lille"],
    "se": ["sweden", "sverige", "stockholm", "gothenburg", "göteborg", "malmö"],
    "dk": ["denmark", "danmark", "copenhagen", "københavn", "aarhus"],
    "no": ["norway", "norge", "oslo", "bergen"],
    "fi": ["finland", "suomi", "helsinki", "espoo", "tampere"],
    "ie": ["ireland", "dublin", "cork", "galway"],
    "it": ["italy", "italia", "milan", "milano", "rome", "roma", "turin", "torino"],
}
_http = session()


def country_of(location):
    loc = (location or "").lower()
    return next((c for c, words in PLACES.items() if any(w in loc for w in words)), None)


def collect_all(days):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    for page in range(1, MAX_PAGES + 1):
        r = _http.get(URL, params={"page": page}, timeout=30)
        r.raise_for_status()
        jobs = r.json()["data"]
        for j in jobs:
            country = country_of(j["location"])
            if country and is_relevant(j["title"]):
                yield to_row(j, country)
        if not jobs or datetime.fromtimestamp(jobs[-1]["created_at"], timezone.utc) < since:
            break
        time.sleep(1)


def to_row(j, country):
    return {
        "source": "arbeitnow", "source_id": j["slug"], "country": country, "search_term": None,
        "title": j["title"], "company": j.get("company_name"), "location": j.get("location"), "region": None,
        "description": j.get("description"),  # HTML, entity-escaped
        "salary_min": None, "salary_max": None, "salary_currency": CURRENCY[country],
        "salary_period": None, "salary_text": None,
        "contract_type": ", ".join(j.get("job_types") or []) or None,
        "posted_at": datetime.fromtimestamp(j["created_at"], timezone.utc).isoformat(),
        "url": j.get("url"), "raw": j,
    }
