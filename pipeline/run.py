"""Build the `enriched` and `fx_ppp` tables. Usage: uv run python -m pipeline.run [--limit N]

Safe to rerun: only jobs not yet enriched are processed. Needs a free write lock on the DB (don't run during collect.py).
"""
import argparse
import json

import requests

import db
from config import COUNTRIES, CURRENCY
from pipeline.enrich import enrich

ISO3 = {"us": "USA", "ca": "CAN", "au": "AUS", "nz": "NZL", "ie": "IRL", "nl": "NLD", "de": "DEU", "se": "SWE",
        "it": "ITA", "fr": "FRA", "hk": "HKG", "dk": "DNK", "no": "NOR", "fi": "FIN", "ae": "ARE", "sg": "SGP",
        "my": "MYS", "vn": "VNM"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS enriched (
    job_key VARCHAR PRIMARY KEY, years_required INTEGER, seniority VARCHAR, text_lang VARCHAR,
    local_lang_required BOOLEAN, visa VARCHAR, skills VARCHAR[], annual_min DOUBLE, annual_max DOUBLE
);
CREATE TABLE IF NOT EXISTS fx_ppp (
    country VARCHAR PRIMARY KEY, currency VARCHAR, per_usd DOUBLE, ppp_factor DOUBLE, ppp_year INTEGER, fetched DATE
);"""


def load_fx_ppp(con):
    rates = requests.get("https://open.er-api.com/v6/latest/USD", timeout=30).json()["rates"]
    wb = requests.get("https://api.worldbank.org/v2/country/" + ";".join(ISO3.values()) +
                      "/indicator/PA.NUS.PPP?format=json&mrnev=1&per_page=100", timeout=30).json()[1]
    ppp = {r["countryiso3code"]: (r["value"], int(r["date"])) for r in wb if r["value"]}
    for c, iso in ISO3.items():
        cur = CURRENCY[c]
        if cur not in rates or iso not in ppp:
            print(f"WARN no fx/ppp for {c} ({cur}, {iso})")
            continue
        con.execute("INSERT OR REPLACE INTO fx_ppp VALUES (?, ?, ?, ?, ?, current_date)",
                    [c, cur, rates[cur], ppp[iso][0], ppp[iso][1]])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int)
    a = p.parse_args()
    con = db.connect()
    con.execute(SCHEMA)
    load_fx_ppp(con)
    cols = ["job_key", "title", "description", "salary_min", "salary_max", "salary_period"]
    todo = con.execute(f"SELECT {', '.join(cols)} FROM jobs WHERE job_key NOT IN (SELECT job_key FROM enriched)"
                       + (f" LIMIT {a.limit}" if a.limit else "")).fetchall()
    out = []
    for r in todo:
        e = enrich(dict(zip(cols, r)))
        out.append([r[0], e["years_required"], e["seniority"], e["text_lang"], e["local_lang_required"],
                    e["visa"], e["skills"], e["annual_min"], e["annual_max"]])
    if out:
        con.executemany("INSERT INTO enriched VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", out)
    print(f"enriched {len(out)} new jobs")

    # One flat view for analysis and the app: salary in local, USD and PPP-adjusted international $.
    con.execute("""
        CREATE OR REPLACE VIEW jobs_enriched AS
        SELECT j.*, e.* EXCLUDE (job_key),
            e.annual_min / f.per_usd AS annual_min_usd, e.annual_max / f.per_usd AS annual_max_usd,
            e.annual_min / f.ppp_factor AS annual_min_ppp, e.annual_max / f.ppp_factor AS annual_max_ppp
        FROM jobs j JOIN enriched e USING (job_key) LEFT JOIN fx_ppp f ON f.country = j.country""")


if __name__ == "__main__":
    main()
