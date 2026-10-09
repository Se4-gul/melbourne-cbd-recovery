"""
Fetch City of Melbourne Pedestrian Counting System data.

Pulls two datasets from the CoM Opendatasoft portal into data/raw/:
  1. Hourly pedestrian counts (~1.6M rows, rolling 24-month window)
  2. Sensor locations (134 sensors, with install dates and status)

Why this downloads month-by-month
---------------------------------
The portal's export endpoint streams the full 1.6M-row file very slowly and
will silently truncate on long connections — you get a partial parquet file
with no error. Requesting one month at a time (via a `where` filter) takes
~7 seconds per month, is resumable, and is verifiable. Slightly more code,
much less chance of quietly analysing half your data.

Usage:
    python src/fetch_data.py            # resumes; skips months already on disk
    python src/fetch_data.py --force    # re-download everything

Note: the portal rate-limits to 5000 requests/day per IP. A full run uses ~26.
"""

from __future__ import annotations

import argparse
import io
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

BASE = "https://melbournetestbed.opendatasoft.com/api/explore/v2.1/catalog/datasets"
COUNTS_ID = "pedestrian-counting-system-monthly-counts-per-hour"
SENSORS_ID = "pedestrian-counting-system-sensor-locations"

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CHUNKS = RAW / "monthly"

TIMEOUT = 120


def month_starts(first: date, last: date) -> list[date]:
    """Every month start from `first` through the month containing `last`."""
    out, cur = [], first.replace(day=1)
    while cur <= last:
        out.append(cur)
        cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out


def next_month(d: date) -> date:
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def get_date_bounds() -> tuple[date, date]:
    """Ask the API what the current rolling window actually covers."""
    r = requests.get(
        f"{BASE}/{COUNTS_ID}/records",
        params={"select": "min(sensing_date) as lo, max(sensing_date) as hi", "limit": 1},
        timeout=30,
    )
    r.raise_for_status()
    row = r.json()["results"][0]
    lo = pd.to_datetime(row["lo"]).date()
    hi = pd.to_datetime(row["hi"]).date()
    return lo, hi


def download_parquet(dataset_id: str, dest: Path, where: str | None = None) -> int:
    """Download one parquet export. Returns row count. Writes atomically."""
    params = {}
    if where:
        params["where"] = where

    r = requests.get(f"{BASE}/{dataset_id}/exports/parquet", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    body = r.content

    if len(body) < 8 or body[-4:] != b"PAR1":
        raise RuntimeError("truncated download (missing parquet footer) — re-run")

    df = pd.read_parquet(io.BytesIO(body))
    tmp = dest.with_suffix(".part")
    df.to_parquet(tmp, index=False)
    tmp.rename(dest)
    return len(df)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="re-download existing files")
    args = ap.parse_args()

    CHUNKS.mkdir(parents=True, exist_ok=True)

    lo, hi = get_date_bounds()
    print(f"Portal window: {lo} -> {hi}")
    print("(this is a ROLLING window — it will differ if you run this next month)\n")

    # --- monthly count chunks -------------------------------------------------
    total = 0
    for start in month_starts(lo, hi):
        tag = start.strftime("%Y-%m")
        dest = CHUNKS / f"{tag}.parquet"

        if dest.exists() and not args.force:
            total += len(pd.read_parquet(dest, columns=["id"]))
            print(f"  [skip]  {tag}")
            continue

        end = next_month(start)
        where = f"sensing_date>=date'{start}' and sensing_date<date'{end}'"
        try:
            n = download_parquet(COUNTS_ID, dest, where=where)
        except Exception as e:
            print(f"  [FAIL]  {tag}: {e}", file=sys.stderr)
            return 1
        total += n
        print(f"  [ok]    {tag}  {n:,} rows")

    # --- combine --------------------------------------------------------------
    print(f"\nCombining {total:,} rows...")
    frames = [pd.read_parquet(f) for f in sorted(CHUNKS.glob("*.parquet"))]
    counts = pd.concat(frames, ignore_index=True)

    before = len(counts)
    counts = counts.drop_duplicates(subset=["location_id", "sensing_date", "hourday"])
    if before != len(counts):
        print(f"  dropped {before - len(counts):,} duplicate sensor-hours (month boundaries)")

    counts.to_parquet(RAW / "pedestrian_counts.parquet", index=False)
    print(f"  -> data/raw/pedestrian_counts.parquet  ({len(counts):,} rows)")

    # --- sensors --------------------------------------------------------------
    n = download_parquet(SENSORS_ID, RAW / "sensor_locations.parquet")
    print(f"  -> data/raw/sensor_locations.parquet   ({n} sensors)")

    # --- provenance -----------------------------------------------------------
    (RAW / "FETCHED_AT.txt").write_text(
        f"fetched_utc: {datetime.now(timezone.utc).isoformat()}\n"
        f"window: {lo} to {hi}\n"
        f"rows: {len(counts)}\n\n"
        "The counts dataset is a rolling 24-month window: the oldest data is\n"
        "silently dropped as new data arrives. Re-downloading later gives you a\n"
        "DIFFERENT date range, not a superset. If you have results you care\n"
        "about, keep data/raw/ and note this timestamp in the writeup.\n"
    )

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
