"""Write one CSV per country (deduplicated jobs) to data/countries/. Usage: uv run python export.py"""
import duckdb

import db
from config import COUNTRIES

out = db.DB_PATH.parent / "countries"
out.mkdir(exist_ok=True)
with duckdb.connect(str(db.DB_PATH), read_only=True) as con:
    for code, name in COUNTRIES.items():
        path = out / f"{code}_{name.split(' (')[0].replace(' ', '_')}.csv"
        n = con.execute(f"COPY (SELECT * FROM jobs WHERE country = ? ORDER BY posted_at DESC) TO '{path}' (HEADER)", [code]).fetchone()[0]
        print(f"{name}: {n} jobs -> {path.name}")
