"""The 7 project questions as pandas functions over relevant jobs (role != 'Other').

Run all and save CSVs:  uv run python -m analysis.questions      (needs the DB free of writers)
Each function takes the jobs_enriched DataFrame `d` and returns a table with one row per country (or country x X).
Countries with fewer than MIN_N jobs are flagged `low_sample`: don't rank on them.
"""
import duckdb
import pandas as pd
import requests

import db
from config import COUNTRIES
from pipeline.enrich import ENTRY_TITLE
from pipeline.run import ISO3

MIN_N = 30
OUT = db.DB_PATH.parent / "results"


def load():
    with duckdb.connect(str(db.DB_PATH), read_only=True) as con:
        d = con.execute("SELECT * EXCLUDE (description), length(description) AS description_len FROM jobs_enriched").df()
    d = d[d["role"] != "Other"].copy()
    d["country_name"] = d["country"].map(COUNTRIES)
    d["entry_title"] = d["title"].fillna("").map(is_entry_title)
    return d


def is_entry_title(title):
    return bool(ENTRY_TITLE.search(title))


def population():
    wb = requests.get("https://api.worldbank.org/v2/country/" + ";".join(ISO3.values()) +
                      "/indicator/SP.POP.TOTL?format=json&mrnev=1&per_page=100", timeout=30).json()[1]
    by_iso = {r["countryiso3code"]: r["value"] for r in wb}
    return {c: by_iso.get(iso) for c, iso in ISO3.items()}


def _flag(t, n):
    t["low_sample"] = n < MIN_N
    return t


def q1_volume(d, pop=None):
    """Relevant jobs and entry-level jobs per country, plus entry-level per million people."""
    g = d.groupby("country_name")
    t = pd.DataFrame({"jobs": g.size(), "entry_jobs": g["seniority"].apply(lambda s: (s == "entry").sum())})
    if pop:
        m = d.groupby("country_name")["country"].first().map(pop) / 1e6
        t["entry_per_million_people"] = (t["entry_jobs"] / m).round(1)
    return _flag(t, t["jobs"]).sort_values("jobs", ascending=False)


def q2_accessibility(d):
    """Entry share, and how many 'junior'-titled jobs still ask for 3+ years (junior inflation)."""
    g = d.groupby("country_name")
    t = pd.DataFrame({
        "jobs": g.size(),
        "entry_share": g["seniority"].apply(lambda s: (s == "entry").mean()).round(3),
        "median_years_asked": g["years_required"].median(),
        "years_stated_share": g["years_required"].apply(lambda s: s.notna().mean()).round(3),
    })
    j = d[d["entry_title"] & d["years_required"].notna()].groupby("country_name")["years_required"]
    t["junior_titled_n"] = j.size()
    t["junior_asks_3plus_share"] = j.apply(lambda s: (s >= 3).mean()).round(3)
    return _flag(t, t["jobs"]).sort_values("entry_share", ascending=False)


def q3_pay(d):
    """Median annual pay of entry-level jobs in PPP-adjusted international $ and nominal USD; n = jobs with pay."""
    e = d[(d["seniority"] == "entry") & d["annual_min_ppp"].notna()].copy()
    e["mid_ppp"] = (e["annual_min_ppp"] + e["annual_max_ppp"]) / 2
    e["mid_usd"] = (e["annual_min_usd"] + e["annual_max_usd"]) / 2
    g = e.groupby(["country_name", "role"])
    t = pd.DataFrame({"n_with_pay": g.size(), "median_ppp": g["mid_ppp"].median().round(0), "median_usd": g["mid_usd"].median().round(0)})
    total = d.groupby(["country_name", "role"]).size().reindex(t.index)
    t["pay_coverage"] = (t["n_with_pay"] / total).round(3)
    t["low_sample"] = t["n_with_pay"] < 10
    return t.sort_values("median_ppp", ascending=False)


def q4_language(d):
    """Share of jobs written in / requiring a non-English language."""
    g = d.groupby("country_name")
    t = pd.DataFrame({
        "jobs": g.size(),
        "non_english_text": g["text_lang"].apply(lambda s: (s.dropna() != "en").mean()).round(3),
        "local_lang_required": g["local_lang_required"].mean().round(3),
        "either": g.apply(lambda x: ((x["text_lang"].notna() & (x["text_lang"] != "en")) | x["local_lang_required"]).mean()).round(3),
    })
    return _flag(t, t["jobs"]).sort_values("either")


def q5_visa(d):
    """Visa wording by country. Only meaningful where descriptions are full text, so n_full is reported."""
    d = d.assign(full=d["description_len"] > 800)
    g = d.groupby("country_name")
    t = pd.DataFrame({"jobs": g.size(), "n_full_text": g["full"].sum()})
    for v in ["sponsorship_offered", "right_to_work_required"]:
        t[v] = g["visa"].apply(lambda s, v=v: (s == v).mean()).round(3)
    return _flag(t, t["n_full_text"]).sort_values("sponsorship_offered", ascending=False)


def q6_skills(d, top=15):
    """Share of jobs mentioning each skill, per country (top N overall)."""
    s = d[["country_name", "skills"]].explode("skills").dropna()
    n = d.groupby("country_name").size()
    share = s.groupby(["country_name", "skills"]).size().unstack(fill_value=0).div(n, axis=0).round(3)
    return share[share.mean().sort_values(ascending=False).head(top).index]


def q7_geography(d, top=5):
    """Top cities per country with entry-level counts."""
    g = d.dropna(subset=["location"]).groupby(["country_name", "location"])
    t = pd.DataFrame({"jobs": g.size(), "entry_jobs": g["seniority"].apply(lambda s: (s == "entry").sum())})
    return t.sort_values("jobs", ascending=False).groupby(level=0).head(top).sort_index()


def run_all():
    d = load()
    OUT.mkdir(exist_ok=True)
    results = {"q1_volume": q1_volume(d, population()), "q2_accessibility": q2_accessibility(d), "q3_pay": q3_pay(d),
               "q4_language": q4_language(d), "q5_visa": q5_visa(d), "q6_skills": q6_skills(d), "q7_geography": q7_geography(d)}
    for name, t in results.items():
        t.to_csv(OUT / f"{name}.csv")
        print(f"\n== {name} ==\n{t.to_string()}")


if __name__ == "__main__":
    run_all()
