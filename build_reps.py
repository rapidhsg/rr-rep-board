"""Build data/reps.json for the Rapid Rep Board from rapidhsg/rr-metrics-data.

Every number comes from rules/rr_metrics.py (the certified rules in rules/RULES.md).
This script only picks the date windows and the reps. It does no counting of its own.

    python build_reps.py                 # clones rr-metrics-data (main + data branch) into a temp folder
    RR_METRICS_DIR=path python build_reps.py   # use an existing clone of main (data branch fetched alongside)

Env:
    GH_TOKEN        optional read-only token for rapidhsg/rr-metrics-data (needed if the repo is private)
    RR_METRICS_DIR  optional path to a local clone of the main branch
    RR_DATA_DIR     optional path to a local checkout of the data branch
    REPORT_DATE     optional YYYY-MM-DD to build the board as of another day (default: today, Eastern)
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
REPO = "rapidhsg/rr-metrics-data"
OUT = Path(__file__).resolve().parent / "data" / "reps.json"

# Board column order. Left: name shown on the board. Right: exact AccuLynx Primary Salesperson
# (must be in settings.json sales_team). Marco and Josh are left out on purpose.
REPS = [
    ("Mike Dietrich", "Michael Dietrich"),
    ("Francesco Ambrosio", "Francesco Ambrosio"),
    ("Joe Young", "Joseph Young"),
    ("Franco Querlim", "Querlim Franco"),
    ("Daniel Leverich", "Dan Leverich"),
    ("Leomar Santana", "Leo Santana"),
]


def clone(branch, dest):
    tok = os.environ.get("GH_TOKEN")
    url = f"https://x-access-token:{tok}@github.com/{REPO}.git" if tok else f"https://github.com/{REPO}.git"
    subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--branch", branch, url, str(dest)], check=True)


def get_sources():
    main = os.environ.get("RR_METRICS_DIR")
    data = os.environ.get("RR_DATA_DIR")
    tmp = Path(tempfile.mkdtemp(prefix="rr-metrics-"))
    if not main:
        main = tmp / "main"
        clone("main", main)
    if not data:
        data = tmp / "data"
        clone("data", data)
    return Path(main), Path(data)


def periods(today):
    import pandas as pd
    t = pd.Timestamp(today).normalize()
    mon = t - pd.Timedelta(days=t.weekday())                     # week = Monday to Sunday
    q = (t.month - 1) // 3
    q_start = pd.Timestamp(t.year, q * 3 + 1, 1)
    q_end = q_start + pd.offsets.QuarterEnd(0)
    return {
        "week": (mon, mon + pd.Timedelta(days=6)),
        "month": (t.replace(day=1), t + pd.offsets.MonthEnd(0)),
        "quarter": (q_start, q_end),
        "year": (pd.Timestamp(t.year, 1, 1), pd.Timestamp(t.year, 12, 31)),
        "_q": q + 1,
        # weeks counted Monday to Sunday; week 1 is the week the quarter starts in
        "_wk": min(13, (mon - (q_start - pd.Timedelta(days=q_start.weekday()))).days // 7 + 1),
    }


def main():
    main_dir, data_dir = get_sources()
    sys.path.insert(0, str(main_dir / "rules"))
    import rr_metrics as rr

    status = json.loads((data_dir / "data" / "status.json").read_text())
    pulled = datetime.fromisoformat(status["job_export_raw"]["runDate"].replace("Z", "+00:00")).astimezone(ET)
    today = datetime.fromisoformat(os.environ["REPORT_DATE"]).date() if os.environ.get("REPORT_DATE") else datetime.now(ET).date()

    df = rr.load(str(data_dir / "data" / "job_export_raw_latest.csv"))
    names = [acc for _, acc in REPS]
    missing = [n for n in names if n not in rr.SALES_TEAM]
    if missing:
        sys.exit(f"Not on the sales_team roster in settings.json: {missing}. Ask Joe.")

    P = periods(today)
    ca = df["Contract Amount"]
    sp = df["Primary Salesperson"]

    # Masks from rr_metrics, one set per window. Close rate and sits = quarter to date, GP = year to date.
    M = {k: rr.masks(df, *P[k], reps=names) for k in ["week", "month", "quarter", "year"]}

    def rep_block(who):
        r = sp.isin(who)
        mq, my = M["quarter"], M["year"]
        sits_cr = int((mq["close_sits_team"] & r).sum())
        sold_cr = int((mq["close_sold_team"] & r).sum())
        gp_profit = float(df.loc[my["gp_jobs"] & r, "Profit"].sum())
        gp_contract = float(ca[my["gp_jobs"] & r].sum())
        return {
            "close_rate": round(sold_cr / sits_cr, 4) if sits_cr else 0,
            "close_counts": {"approved": sold_cr, "demos": sits_cr},
            "sits": int((mq["sits"] & r).sum()),
            "sales": {k: {"amount": round(float(ca[M[k]["sales"] & r].sum())),
                          "count": int((M[k]["jobs_sold"] & r).sum())} for k in M},
            "gp": {"amount": round(gp_profit), "pct": round(gp_profit / gp_contract, 4) if gp_contract else 0},
            # Avg Ticket (RULES.md section 4) = Sales $ / Jobs Sold, same records as the sales rows.
            "avg_ticket": {k: (round(float(ca[M[k]["sales"] & r].sum()) / n) if (n := int((M[k]["jobs_sold"] & r).sum())) else 0)
                           for k in ["quarter", "year"]},
        }

    w0, w1 = P["week"]
    out = {
        "sample": False,
        "updated": pulled.isoformat(timespec="seconds"),
        "periods": {
            "week": f"{w0:%b} {w0.day} – {w1:%b} {w1.day}",
            "month": f"{P['month'][0]:%B}",
            "quarter": f"Q{P['_q']} {today.year}",
            "year": str(today.year),
            "close_rate": f"Q{P['_q']} {today.year}",
            "sits": f"Q{P['_q']} {today.year}",
            "week_of_quarter": f"{P['_wk']} / 13",
        },
        "reps": [{"name": shown, **rep_block([acc])} for shown, acc in REPS],
        "team": rep_block(names),
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote {OUT} (report date {today}, data pulled {pulled:%b %d %I:%M %p} ET)")


if __name__ == "__main__":
    main()
