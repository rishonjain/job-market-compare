"""Company career pages via public ATS JSON (Greenhouse, Lever, Ashby, SmartRecruiters, Workable).

Companies come from ats_companies.csv (ats,token) plus tokens discovered in the url column of data/jobs.duckdb.
"""
import csv
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb

import config
from collectors.http import session
from db import DB_PATH

COUNTRIES = list(config.COUNTRIES)
CSV_PATH = Path(__file__).parent.parent / "ats_companies.csv"
_http = session()

# Lowercase keywords per country; matched on word boundaries so "de" or "sg" can't hit inside other words.
PLACES = {
    "us": ["united states", "usa", "u.s.", "us", "new york", "san francisco", "seattle", "austin", "boston", "chicago", "los angeles", "atlanta", "denver", "washington, dc", "palo alto", "mountain view", "sunnyvale", "san jose", "california", "texas", "massachusetts", "ny", "ca, us"],
    "ca": ["canada", "toronto", "vancouver", "montreal", "montréal", "ottawa", "calgary", "waterloo", "ontario", "british columbia"],
    "au": ["australia", "sydney", "melbourne", "brisbane", "perth", "canberra", "adelaide"],
    "nz": ["new zealand", "auckland", "wellington", "christchurch"],
    "ie": ["ireland", "dublin", "cork", "galway", "limerick"],
    "nl": ["netherlands", "amsterdam", "rotterdam", "utrecht", "eindhoven", "the hague", "den haag"],
    "de": ["germany", "deutschland", "berlin", "munich", "münchen", "hamburg", "frankfurt", "cologne", "köln", "stuttgart", "düsseldorf", "leipzig"],
    "se": ["sweden", "stockholm", "gothenburg", "göteborg", "malmö", "malmo", "uppsala"],
    "it": ["italy", "italia", "milan", "milano", "rome", "roma", "turin", "torino", "bologna"],
    "fr": ["france", "paris", "lyon", "marseille", "toulouse", "nantes", "lille", "bordeaux"],
    "hk": ["hong kong"],
    "dk": ["denmark", "copenhagen", "københavn", "aarhus"],
    "no": ["norway", "oslo", "bergen", "trondheim"],
    "fi": ["finland", "helsinki", "espoo", "tampere"],
    "ae": ["united arab emirates", "uae", "dubai", "abu dhabi"],
    "sg": ["singapore"],
    "my": ["malaysia", "kuala lumpur"],
    "vn": ["vietnam", "viet nam", "ho chi minh", "hanoi", "da nang"],
}
_PLACE_RE = {c: re.compile(r"(?<!\w)(?:%s)(?!\w)" % "|".join(map(re.escape, ps))) for c, ps in PLACES.items()}


def country_of(text):
    """Country code if the location text names exactly one of our countries, else None (ambiguous multi-country is dropped)."""
    t = (text or "").lower()
    hits = [c for c, rx in _PLACE_RE.items() if rx.search(t)]
    return hits[0] if len(hits) == 1 else None


def wanted_title(title):
    t = (title or "").lower()
    return any(term in t for terms in [config.TERMS, *config.LOCAL_TERMS.values()] for term in terms)


def _iso_ms(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat() if ms else None


def _row(source, token, company, j, sid, title, loc, desc, posted, url, term_country, **extra):
    country = country_of(loc) or term_country
    if not country or not wanted_title(title):
        return None
    base = dict.fromkeys(["region", "salary_min", "salary_max", "salary_currency", "salary_period", "salary_text", "contract_type"])
    base.update(extra)
    return {
        **base, "source": source, "source_id": f"{token}:{sid}", "country": country, "search_term": None,
        "title": title, "company": company, "location": loc, "description": desc,
        "posted_at": posted, "url": url, "raw": j,
    }


def greenhouse(token):
    j = _http.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs", params={"content": "true"}, timeout=30)
    j.raise_for_status()
    for x in j.json()["jobs"]:
        loc = (x.get("location") or {}).get("name")
        yield _row("greenhouse", token, x.get("company_name") or token, x, x["id"], x["title"], loc,
                   x.get("content"), x.get("first_published") or x.get("updated_at"), x.get("absolute_url"), None)


def lever(token):
    r = _http.get(f"https://api.lever.co/v0/postings/{token}", params={"mode": "json"}, timeout=30)
    r.raise_for_status()
    for x in r.json():
        c = x.get("categories") or {}
        loc = " / ".join(filter(None, [c.get("location"), *(c.get("allLocations") or [])]))
        yield _row("lever", token, token, x, x["id"], x["text"], loc, x.get("descriptionPlain"),
                   _iso_ms(x.get("createdAt")), x.get("hostedUrl"), None, contract_type=c.get("commitment"))


def ashby(token):
    r = _http.get(f"https://api.ashbyhq.com/posting-api/job-board/{token}", params={"includeCompensation": "true"}, timeout=30)
    r.raise_for_status()
    for x in r.json()["jobs"]:
        loc = " / ".join(filter(None, [x.get("location"), *(s.get("location") for s in x.get("secondaryLocations") or [])]))
        country = (((x.get("address") or {}).get("postalAddress")) or {}).get("addressCountry")
        yield _row("ashby", token, token, x, x["id"], x["title"], f"{loc} {country or ''}".strip(), x.get("descriptionPlain"),
                   x.get("publishedAt"), x.get("jobUrl"), None, contract_type=x.get("employmentType"),
                   salary_text=(x.get("compensation") or {}).get("compensationTierSummary"))


def smartrecruiters(token):
    for offset in range(0, 2000, 100):
        r = _http.get(f"https://api.smartrecruiters.com/v1/companies/{token}/postings", params={"limit": 100, "offset": offset}, timeout=30)
        r.raise_for_status()
        content = r.json()["content"]
        for x in content:
            l = x.get("location") or {}
            loc = ", ".join(filter(None, [l.get("city"), l.get("country")]))
            # list endpoint has no description; shortcut: fetch x["ref"] per job if descriptions are needed
            yield _row("smartrecruiters", token, (x.get("company") or {}).get("name") or token, x, x["id"], x["name"], loc,
                       None, x.get("releasedDate"), f"https://jobs.smartrecruiters.com/{token}/{x['id']}", None,
                       contract_type=(x.get("typeOfEmployment") or {}).get("label"))
        if len(content) < 100:
            break


def workable(token):
    r = _http.get(f"https://apply.workable.com/api/v1/widget/accounts/{token}", params={"details": "true"}, timeout=30)
    r.raise_for_status()
    d = r.json()
    for x in d["jobs"]:
        loc = ", ".join(filter(None, [x.get("city"), x.get("country")]))
        yield _row("workable", token, d.get("name") or token, x, x["shortcode"], x["title"], loc, x.get("description"),
                   x.get("published_on") or x.get("created_at"), x.get("url"), None, contract_type=x.get("employment_type"))


FETCHERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby, "smartrecruiters": smartrecruiters, "workable": workable}
DISCOVER = re.compile(r"(?:boards\.greenhouse\.io|job-boards\.greenhouse\.io|jobs\.lever\.co|jobs\.ashbyhq\.com|jobs\.smartrecruiters\.com|apply\.workable\.com)/([\w.-]+)")
_HOST_ATS = {"greenhouse.io": "greenhouse", "lever.co": "lever", "ashbyhq.com": "ashby", "smartrecruiters.com": "smartrecruiters", "workable.com": "workable"}


def companies():
    seen = {tuple(r.values()) for r in csv.DictReader(CSV_PATH.open())}
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        urls = [u for (u,) in con.execute("SELECT DISTINCT url FROM postings WHERE url IS NOT NULL").fetchall()]
        con.close()
    except duckdb.Error:  # missing or locked db: discovery is optional
        urls = []
    for u in urls:
        m = DISCOVER.search(u)
        host = next((a for h, a in _HOST_ATS.items() if h in u), None)
        if m and host:
            seen.add((host, m.group(1)))
    return sorted(seen)


def _fetch_company(item):
    ats, token = item
    time.sleep(0.3)
    try:
        return [r for r in FETCHERS[ats](token) if r]
    except Exception as e:  # one dead/renamed board must not stop the run
        print(f"SKIP {ats}/{token}: {e}", flush=True)
        return []


def collect_all(days):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with ThreadPoolExecutor(4) as pool:
        for rows in pool.map(_fetch_company, companies()):
            for r in rows:
                # keep postings with no/unparseable date: open ads matter even when the ATS hides when they were posted
                try:
                    old = datetime.fromisoformat(str(r["posted_at"]).replace("Z", "+00:00")).astimezone(timezone.utc) < since
                except ValueError:
                    old = False
                if not old:
                    yield r
