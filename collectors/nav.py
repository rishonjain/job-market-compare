"""Norway's NAV job board (arbeidsplassen.nav.no) public search — no key needed."""
import time

from collectors.http import session

COUNTRIES = ["no"]
URL = "https://arbeidsplassen.nav.no/stillinger/api/search"
PAGE = 25  # fixed by the API; the `size` param is ignored
MAX_PAGES = 20
_http = session()


def collect(country, term, days, max_pages=MAX_PAGES):
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))
    for page in range(max_pages):
        r = _http.get(URL, params={"q": f'"{term}"', "sort": "published", "from": page * PAGE}, timeout=30)
        r.raise_for_status()
        hits = r.json()["hits"]["hits"]
        for h in hits:
            j = h["_source"]
            if j["published"][:10] < cutoff:
                return  # sorted newest first
            yield to_row(j, term)
        if len(hits) < PAGE:
            return
        time.sleep(2)  # NAV answers 429 quickly if hit faster


def to_row(j, term):
    loc = (j.get("locationList") or [{}])[0]
    return {
        "source": "nav", "source_id": j["uuid"], "country": "no", "search_term": term,
        "title": j.get("title"), "company": j.get("businessName") or (j.get("employer") or {}).get("name"),
        "location": loc.get("city"), "region": loc.get("county"),
        # search results carry only an AI summary; the full text exists only as HTML on the ad page
        "description": (j.get("generatedSearchMetadata") or {}).get("shortSummary"),
        "salary_min": None, "salary_max": None, "salary_currency": "NOK", "salary_period": None, "salary_text": None,
        "contract_type": None, "posted_at": j.get("published"),
        "url": f"https://arbeidsplassen.nav.no/stillinger/stilling/{j['uuid']}", "raw": j,
    }
