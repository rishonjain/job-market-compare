"""SEEK group search JSON (the same endpoint their sites call): AU, NZ, HK (JobsDB), MY + SG (JobStreet)."""
import time

from collectors.http import session

# country -> (host, siteKey, source name, currency)
SITES = {
    "au": ("www.seek.com.au", "AU-Main", "seek", "AUD"),
    "nz": ("www.seek.co.nz", "NZ-Main", "seek", "NZD"),
    "hk": ("hk.jobsdb.com", "HK-Main", "jobsdb", "HKD"),
    "my": ("my.jobstreet.com", "MY-Main", "jobstreet", "MYR"),
    "sg": ("sg.jobstreet.com", "SG-Main", "jobstreet", "SGD"),
}
COUNTRIES = list(SITES)
PER_PAGE = 100
_http = session({"User-Agent": "Mozilla/5.0"})  # the endpoint answers browsers only


def collect(country, term, days, max_pages=10):
    host, site_key, source, currency = SITES[country]
    for page in range(1, max_pages + 1):
        params = {"siteKey": site_key, "keywords": term, "pageSize": PER_PAGE, "page": page, "dateRange": days}
        r = _http.get(f"https://{host}/api/jobsearch/v5/search", params=params, timeout=30)
        r.raise_for_status()
        data = r.json()["data"]
        for j in data:
            yield to_row(j, country, term, host, source, currency)
        time.sleep(1.5)
        if len(data) < PER_PAGE:
            break


def to_row(j, country, term, host, source, currency):
    locs = j.get("locations") or []
    hierarchy = (locs[0].get("seoHierarchy") or []) if locs else []
    # shortcut: search results carry only a teaser + bullet points, not the full ad; fetch the detail page if you need skills text
    description = " ".join([j.get("teaser") or ""] + (j.get("bulletPoints") or [])).strip() or None
    return {
        "source": source, "source_id": str(j["id"]), "country": country, "search_term": term,
        "title": j.get("title"), "company": j.get("companyName") or (j.get("advertiser") or {}).get("description"),
        "location": locs[0]["label"] if locs else None,
        "region": hierarchy[-1]["contextualName"] if hierarchy else None,
        "description": description,
        "salary_min": None, "salary_max": None, "salary_currency": currency,  # salary only comes as free text ("$140k-$170k")
        "salary_period": None, "salary_text": j.get("salaryLabel") or None,
        "contract_type": ", ".join(j.get("workTypes") or []) or None,
        "posted_at": j.get("listingDate"), "url": f"https://{host}/job/{j['id']}", "raw": j,
    }
