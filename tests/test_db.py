import db


def row(source_id, **kw):
    r = dict.fromkeys(db.COLUMNS)
    r.update(source="t", source_id=source_id, posted_at="2026-10-19T08:00:00Z", raw={"x": 1})
    r.update(kw)
    return r


def test_jobs_view_merges_same_job_across_sources():
    con = db.connect(":memory:")
    db.upsert(con, [
        row("1", source="indeed", country="de", company="Acme GmbH", title="Data Analyst (m/w/d)", description="short"),
        row("2", source="linkedin", country="de", company="ACME", title="Data Analyst m/w/d", description="much longer text"),
        row("3", source="linkedin", country="nl", company="ACME", title="Data Analyst m/w/d"),
        row("4", source="topcv", country="vn", company="FPT", title="Chuyên viên phân tích dữ liệu"),
        row("5", source="topcv", country="vn", company="FPT", title="Kỹ sư dữ liệu"),
    ])
    jobs = {r[0]: r for r in con.execute("SELECT country, description, sources FROM jobs WHERE country='de'").fetchall()}
    assert jobs["de"][1] == "much longer text" and sorted(jobs["de"][2]) == ["indeed", "linkedin"]
    assert con.execute("SELECT count(*) FROM jobs").fetchone()[0] == 4  # non-Latin titles must not collapse
    roles = dict(con.execute("SELECT title, role FROM jobs").fetchall())
    assert roles["Data Analyst m/w/d"] == "Data Analyst" and roles["Kỹ sư dữ liệu"] == "Data Engineer"


def test_upsert_keeps_first_seen_and_bumps_last_seen():
    con = db.connect(":memory:")
    assert db.upsert(con, [row("1"), row("2")]) == 2
    first = con.execute("SELECT first_seen FROM postings WHERE source_id = '1'").fetchone()[0]
    assert db.upsert(con, [row("1")]) == 0
    first2, last = con.execute("SELECT first_seen, last_seen FROM postings WHERE source_id = '1'").fetchone()
    assert first2 == first and last > first
