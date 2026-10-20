import pandas as pd

from analysis import questions as q


def sample():
    rows = [  # country, title, seniority, years, lang, local_req, visa, skills, loc, ppp_min, ppp_max, role, desc_len
        ("de", "Junior Data Analyst", "entry", 4, "de", True, "not_mentioned", ["SQL", "Python"], "Berlin", 30000, 40000, "Data Analyst", 2000),
        ("de", "Data Engineer", "mid", None, "en", False, "sponsorship_offered", ["SQL"], "Berlin", None, None, "Data Engineer", 2000),
        ("sg", "Graduate Data Scientist", "entry", 0, "en", False, "not_mentioned", ["Python"], "Singapore", 50000, 50000, "Data Scientist", 100),
    ]
    cols = ["country", "title", "seniority", "years_required", "text_lang", "local_lang_required", "visa", "skills",
            "location", "annual_min_ppp", "annual_max_ppp", "role", "description_len"]
    d = pd.DataFrame(rows, columns=cols)
    d["annual_min_usd"], d["annual_max_usd"] = d["annual_min_ppp"], d["annual_max_ppp"]
    d["country_name"] = d["country"]
    d["entry_title"] = d["title"].map(q.is_entry_title)
    return d


def test_all_questions_run_and_make_sense():
    d = sample()
    assert q.q1_volume(d, {"de": 84e6, "sg": 6e6}).loc["sg", "entry_jobs"] == 1
    a = q.q2_accessibility(d)
    assert a.loc["de", "junior_asks_3plus_share"] == 1.0 and a.loc["sg", "entry_share"] == 1.0
    p = q.q3_pay(d)
    assert p.loc[("de", "Data Analyst"), "median_ppp"] == 35000 and p.loc[("de", "Data Analyst"), "pay_coverage"] == 1.0
    assert q.q4_language(d).loc["de", "either"] == 0.5
    assert q.q5_visa(d).loc["de", "sponsorship_offered"] == 0.5
    assert q.q6_skills(d).loc["de", "SQL"] == 1.0
    assert q.q7_geography(d).loc[("de", "Berlin"), "jobs"] == 2
