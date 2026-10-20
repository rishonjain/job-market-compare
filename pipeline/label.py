"""Hand-label a sample, then score the classifiers against it.

  uv run python -m pipeline.label make [--per-country 20]   -> data/labels.csv (predictions pre-filled)
  (open the CSV, fill the true_* columns, correct wherever the prediction is wrong)
  uv run python -m pipeline.label score                      -> precision / recall per field

true_role: one of the 7 roles, or Other (not a data/analytics job at all).
true_seniority: entry | mid | senior.  true_visa: sponsorship_offered | right_to_work_required | not_mentioned.
true_local_lang: y | n (posting needs a non-English language).
"""
import csv
import sys
from collections import Counter

import duckdb

import db
from pipeline.enrich import clean

PATH = db.DB_PATH.parent / "labels.csv"
FIELDS = {"role": "role", "seniority": "seniority", "visa": "visa", "local_lang": "local_lang_required"}


def make(per_country):
    con = duckdb.connect(str(db.DB_PATH), read_only=True)
    rows = con.execute(f"""
        SELECT * FROM (SELECT job_key, country, source, title, company, description, role, seniority, visa, local_lang_required,
                       row_number() OVER (PARTITION BY country ORDER BY hash(job_key)) AS n FROM jobs_enriched)
        WHERE n <= {int(per_country)} ORDER BY country, n""").fetchall()
    with open(PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["job_key", "country", "source", "title", "company", "snippet",
                    "pred_role", "pred_seniority", "pred_visa", "pred_local_lang",
                    "true_role", "true_seniority", "true_visa", "true_local_lang"])
        for r in rows:
            w.writerow([*r[:4], r[4], clean(r[5])[:700], r[6], r[7], r[8], "y" if r[9] else "n", "", "", "", ""])
    print(f"wrote {len(rows)} rows to {PATH}")


def prf(pairs):
    """pairs: (true, pred). Returns {class: (precision, recall, support)} and accuracy."""
    out = {}
    for c in sorted({t for t, _ in pairs}):
        tp = sum(t == c and p == c for t, p in pairs)
        pp = sum(p == c for _, p in pairs)
        sup = sum(t == c for t, _ in pairs)
        out[c] = (tp / pp if pp else 0.0, tp / sup, sup)
    return out, sum(t == p for t, p in pairs) / len(pairs)


def score():
    with open(PATH, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["true_role"].strip()]
    if not rows:
        sys.exit("no labeled rows yet: fill the true_* columns in " + str(PATH))
    print(f"{len(rows)} labeled rows")
    for name in FIELDS:
        pairs = [(r[f"true_{name}"].strip(), r[f"pred_{name}"].strip()) for r in rows if r[f"true_{name}"].strip()]
        res, acc = prf(pairs)
        print(f"\n{name}: accuracy {acc:.0%} on {len(pairs)}")
        for c, (p, rc, n) in res.items():
            print(f"  {c:24s} precision {p:.0%}  recall {rc:.0%}  (n={n})")
    wrong = Counter((r["true_role"], r["pred_role"]) for r in rows if r["true_role"] != r["pred_role"])
    print("\nmost common role mistakes (true -> predicted):", wrong.most_common(5))


if __name__ == "__main__":
    if sys.argv[1:2] == ["make"]:
        make(int(sys.argv[sys.argv.index("--per-country") + 1]) if "--per-country" in sys.argv else 20)
    elif sys.argv[1:2] == ["score"]:
        score()
    else:
        sys.exit(__doc__)
