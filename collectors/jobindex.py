"""Jobindex.dk (Denmark): the search page embeds its results as JSON in `var Stash = {...}`."""
import json
import re
import time
from datetime import date, timedelta

from bs4 import BeautifulSoup

from collectors.http import session

COUNTRIES = ["dk"]
URL = "https://www.jobindex.dk/jobsoegning"
MAX_PAGES = 10
_http = session()


def collect(country, term, days, max_pages=MAX_PAGES):
    since = (date.today() - timedelta(days=days)).isoformat()
    for page in range(1, max_pages + 1):
        r = _http.get(URL, params={"q": f'"{term}"', "sort": "date", "page": page}, timeout=30)
        r.raise_for_status()
        m = re.search(r"var Stash = (\{.*?\});\s*\n", r.text, re.S)
        res = json.loads(m.group(1))["jobsearch/result_app/list"]["storeData"]["searchResponse"]
        for j in res["results"]:
            if j["firstdate"] >= since:
                yield to_row(j, term)
        if page >= res["total_pages"] or res["results"][-1]["firstdate"] < since:
            break
        time.sleep(2)


def to_row(j, term):
    paras = BeautifulSoup(j["html"], "html.parser").find_all("p")  # only the ad teaser is public
    raw = {k: v for k, v in j.items() if k not in ("html", "geojson")}
    return {
        "source": "jobindex", "source_id": j["tid"], "country": "dk", "search_term": term,
        "title": j["headline"], "company": j.get("companytext"), "location": j.get("area"), "region": None,
        "description": "\n".join(p.get_text(" ", strip=True) for p in paras) or None,
        "salary_min": None, "salary_max": None, "salary_currency": "DKK", "salary_period": None,
        "salary_text": json.dumps(j["salary"]) if j.get("salary") else None,
        "contract_type": None, "posted_at": j["firstdate"], "url": j.get("share_url"), "raw": raw,
    }
