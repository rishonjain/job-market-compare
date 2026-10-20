"""Singapore government job portal: https://api.mycareersfuture.gov.sg — no key needed, structured salary."""
import time

from collectors.http import session

COUNTRIES = ["sg"]
URL = "https://api.mycareersfuture.gov.sg/v2/jobs"
PER_PAGE = 100
MAX_PAGES = 10
_http = session()


def collect(country, term, days, max_pages=MAX_PAGES):
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))
    for page in range(max_pages):
        params = {"search": term, "limit": PER_PAGE, "page": page, "sortBy": "new_posting_date"}
        r = _http.get(URL, params=params, timeout=30)
        r.raise_for_status()
        results = r.json()["results"]
        for j in results:
            if j["metadata"]["newPostingDate"] < cutoff:
                return  # sorted newest first
            yield to_row(j, term)
        if len(results) < PER_PAGE:
            return
        time.sleep(1)


def to_row(j, term):
    meta, sal = j["metadata"], j.get("salary") or {}
    district = ((j.get("address") or {}).get("districts") or [{}])[0]
    return {
        "source": "mycareersfuture", "source_id": j["uuid"], "country": "sg", "search_term": term,
        "title": j.get("title"), "company": (j.get("postedCompany") or {}).get("name"),
        "location": district.get("location"), "region": district.get("region"),
        "description": j.get("description"),  # HTML
        "salary_min": sal.get("minimum"), "salary_max": sal.get("maximum"), "salary_currency": "SGD",
        "salary_period": {"Monthly": "month", "Annually": "year", "Hourly": "hour"}.get((sal.get("type") or {}).get("salaryType")),
        "salary_text": None,
        "contract_type": ", ".join(e["employmentType"] for e in j.get("employmentTypes") or []) or None,
        "posted_at": meta.get("newPostingDate"), "url": meta.get("jobDetailsUrl"), "raw": j,
    }
