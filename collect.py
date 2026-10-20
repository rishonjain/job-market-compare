"""Usage: uv run --env-file .env python collect.py [sources...] [--days N] [--countries us de ...]

Any module in collectors/ with COUNTRIES is a source. It exposes either
collect(country, term, days) for search APIs, or collect_all(days) for sources
that list every job at once (company career pages). Both yield db.COLUMNS rows.
"""
import argparse
import importlib
import pkgutil

import collectors
import db
from config import terms_for

SOURCES = {}
for m in pkgutil.iter_modules(collectors.__path__):
    mod = importlib.import_module(f"collectors.{m.name}")
    if hasattr(mod, "COUNTRIES"):
        SOURCES[m.name] = mod


def save(con, label, rows_iter, countries):
    rows = []
    try:
        rows.extend(r for r in rows_iter if not countries or r["country"] in countries)
    except Exception as e:  # keep going; save whatever pages we got
        print(f"FAIL {label}: {e}")
    print(f"{label}: {len(rows)} fetched, {db.upsert(con, rows)} new", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("sources", nargs="*", choices=sorted(SOURCES), default=sorted(SOURCES))
    p.add_argument("--days", type=int, default=2, help="only postings from the last N days (use ~30 for the first backfill)")
    p.add_argument("--countries", nargs="*")
    p.add_argument("--terms", nargs="*", help="only these search terms (default: all in config.py)")
    a = p.parse_args()

    con = db.connect()
    for name in a.sources:
        mod = SOURCES[name]
        if hasattr(mod, "collect_all"):
            save(con, name, mod.collect_all(a.days), a.countries)
            continue
        for country in mod.COUNTRIES:
            if a.countries and country not in a.countries:
                continue
            for term in a.terms or terms_for(country):
                save(con, f"{name} {country} '{term}'", mod.collect(country, term, a.days), None)


if __name__ == "__main__":
    main()
