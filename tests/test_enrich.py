from pipeline.enrich import annual_salary, enrich, seniority, skills, visa, years_required


def test_years_required():
    assert years_required("3+ years of experience in SQL") == 3
    assert years_required("0-2 years experience") == 0
    assert years_required("mindestens 2 Jahre Berufserfahrung") == 2
    assert years_required("We have been growing for 10 years") is None  # no experience context
    assert years_required("1-3 years' experience; 5 years of Python experience") == 1


def test_seniority():
    assert seniority("Junior Data Analyst", 4) == "entry"
    assert seniority("Senior Data Analyst", 0) == "senior"
    assert seniority("Werkstudent Data Science (m/w/d)", None) == "entry"
    assert seniority("Data Analyst", 1) == "entry"
    assert seniority("Data Analyst", 3) == "mid"
    assert seniority("Data Engineer", 6) == "senior"
    assert seniority("Data Analyst", None) == "mid"
    assert seniority("Analytics Lead", 1) == "senior"


def test_visa():
    assert visa("We offer visa sponsorship for the right candidate") == "sponsorship_offered"
    assert visa("Applicants must have the right to work in the UK") == "right_to_work_required"
    assert visa("Unfortunately we cannot sponsor visas") == "right_to_work_required"
    assert visa("Great team and snacks") == "not_mentioned"


def test_skills_case_rules():
    s = skills("Experience with Python, SQL, Power BI and R, plus a great attitude")
    assert {"Python", "SQL", "Power BI", "R"} <= set(s)
    assert "R" not in skills("Our grand strategy is to recruit R&D talent")
    assert "SAS" not in skills("We sas around") and "SAS" in skills("Knowledge of SAS required")


def test_annual_salary():
    assert annual_salary(4000, 5000, "month") == (48000, 60000)
    assert annual_salary(30, None, "hour") == (62400, 62400)
    assert annual_salary(50000, 60000, None) == (None, None)  # unknown period: don't guess
    assert annual_salary(40, 50, "year") == (None, None)  # implausible unit mix-up


def test_enrich_end_to_end():
    r = enrich({"title": "Junior Data Analyst", "description": "<p>Du hast fließend Deutsch und 1 Jahr Erfahrung mit SQL. "
                "Wir bieten Visumsunterstützung. Das ist ein längerer deutscher Text über die Stelle.</p>",
                "salary_min": 3000, "salary_max": 3500, "salary_period": "month"})
    assert r["seniority"] == "entry" and r["years_required"] == 1 and r["local_lang_required"]
    assert r["visa"] == "sponsorship_offered" and "SQL" in r["skills"] and r["text_lang"] == "de"
    assert r["annual_min"] == 36000
