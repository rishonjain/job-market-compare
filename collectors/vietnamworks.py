"""VietnamWorks search API (the one its own site calls). Results include the full description."""
import time
from datetime import datetime, timedelta, timezone

from collectors.http import session

COUNTRIES = ["vn"]
URL = "https://ms.vietnamworks.com/job-search/v1.0/search"
PER_PAGE = 50
_http = session()


def collect(country, term, days, max_pages=10):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    for page in range(max_pages):
        r = _http.post(URL, json={"query": term, "page": page, "hitsPerPage": PER_PAGE}, timeout=30)
        r.raise_for_status()
        data = r.json()["data"]
        for j in data:
            # no server-side date filter, so cut client-side (ISO strings with offsets parse as aware datetimes)
            if datetime.fromisoformat(j["approvedOn"]) >= datetime.fromisoformat(since):
                yield to_row(j, term)
        time.sleep(1.5)
        if len(data) < PER_PAGE:
            break


def to_row(j, term):
    lo, hi = j.get("salaryMin") or None, j.get("salaryMax") or None
    locs = j.get("workingLocations") or []
    desc = " ".join(filter(None, [j.get("jobDescription"), j.get("jobRequirement")])) or None
    return {
        "source": "vietnamworks", "source_id": str(j["jobId"]), "country": "vn", "search_term": term,
        "title": j.get("jobTitle"), "company": j.get("companyName"),
        "location": locs[0].get("cityName") or locs[0].get("address") if locs else j.get("address"), "region": None,
        "description": desc,
        "salary_min": lo, "salary_max": hi, "salary_currency": j.get("salaryCurrency") if lo or hi else None,
        # shortcut: assuming monthly pay (VN norm); salaryPeriodId is undocumented, verify when salary data is analysed
        "salary_period": "month" if lo or hi else None, "salary_text": j.get("prettySalary") or None,
        "contract_type": j.get("jobLevel"), "posted_at": j.get("approvedOn"), "url": j.get("jobUrl"), "raw": j,
    }
