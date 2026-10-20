import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

DB_PATH = Path(__file__).parent / "data" / "jobs.duckdb"

# Every collector returns rows with exactly these keys.
COLUMNS = [
    "source", "source_id", "country", "search_term", "title", "company", "location", "region",
    "description", "salary_min", "salary_max", "salary_currency", "salary_period", "salary_text",
    "contract_type", "posted_at", "url", "raw",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS postings (
    source VARCHAR, source_id VARCHAR, country VARCHAR, search_term VARCHAR,
    title VARCHAR, company VARCHAR, location VARCHAR, region VARCHAR, description VARCHAR,
    salary_min DOUBLE, salary_max DOUBLE, salary_currency VARCHAR, salary_period VARCHAR, salary_text VARCHAR,
    contract_type VARCHAR, posted_at TIMESTAMPTZ, url VARCHAR, raw JSON,
    first_seen TIMESTAMPTZ, last_seen TIMESTAMPTZ,
    PRIMARY KEY (source, source_id)
);

-- One row per real job across sources; keeps the copy with the longest description.
-- shortcut: key ignores city, so one company's identical title in two cities counts once; add location if that matters.
CREATE OR REPLACE VIEW jobs AS
WITH keyed AS (
    SELECT *, country || '|' ||
        regexp_replace(regexp_replace(lower(coalesce(company, '')),
            '\\b(inc|ltd|llc|gmbh|ag|ab|as|aps|asa|oy|oyj|bv|nv|sa|sas|srl|spa|pty|pte|sdn|bhd|limited|corp|co)\\b', '', 'g'),
            '[^\\pL\\pN]+', '', 'g') || '|' ||
        regexp_replace(lower(title), '[^\\pL\\pN]+', '', 'g') AS job_key,
        -- first-pass role from title (order matters); Phase 3 enrichment refines this
        CASE
            WHEN regexp_matches(lower(title), 'machine learning|\\bml\\b|mlops') THEN 'ML Engineer'
            WHEN regexp_matches(lower(title), '\\bai\\b|artificial intelligence|\\bllm|genai|generative') THEN 'AI Engineer'
            WHEN regexp_matches(lower(title), 'data scien|datenwissenschaft') THEN 'Data Scientist'
            WHEN regexp_matches(lower(title), 'data.?engineer|dateningenieur|dataingenj|dataingeni|datainsin|ingénieur.{0,4}données|kỹ sư dữ liệu') THEN 'Data Engineer'
            WHEN regexp_matches(lower(title), 'business analyst') THEN 'Business Analyst'
            WHEN regexp_matches(lower(title), 'data.?anal|datenanalyst|dataanalyt|analyste de données|data analyste|analista dati|phân tích dữ liệu|penganalisis data') THEN 'Data Analyst'
            WHEN regexp_matches(lower(title), 'analy|insight|business intelligence|\\bbi\\b|reporting') THEN 'Analytics (other)'
            ELSE 'Other'
        END AS role
    FROM postings
)
SELECT * EXCLUDE (raw),
    list_distinct(list(source) OVER w) AS sources,
    min(first_seen) OVER w AS job_first_seen,
    max(last_seen) OVER w AS job_last_seen
FROM keyed
WINDOW w AS (PARTITION BY job_key)
QUALIFY row_number() OVER (PARTITION BY job_key ORDER BY length(description) DESC NULLS LAST, source) = 1
"""


def connect(path=None):
    if path is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        path = DB_PATH
    con = duckdb.connect(str(path))
    con.execute(SCHEMA)
    return con


def upsert(con, rows):
    """Insert new postings; for known ones only bump last_seen (lets us measure how long ads stay up)."""
    now = datetime.now(timezone.utc)
    before = con.execute("SELECT count(*) FROM postings").fetchone()[0]
    values = [[r[c] for c in COLUMNS[:-1]] + [json.dumps(r["raw"]), now, now] for r in rows]
    if values:
        con.executemany(
            f"INSERT INTO postings VALUES ({', '.join('?' * (len(COLUMNS) + 2))}) "
            "ON CONFLICT DO UPDATE SET last_seen = excluded.last_seen",
            values,
        )
    return con.execute("SELECT count(*) FROM postings").fetchone()[0] - before
