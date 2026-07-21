"""
Chinatown facades — Step 3: download historical Google Street View facade photos
for each (bbl, year) pair.

Requires: GOOGLE_MAPS_API_KEY env var with Street View Static API enabled.

Cost: the Static API is $7 per 1000 images after the $200 monthly free credit
(about 28,500 images free/month). Every request writes one JPEG.

Usage:
    export GOOGLE_MAPS_API_KEY='...'
    python3 fetch_facades.py           # ~6 target years for all lots (~6k images)
    python3 fetch_facades.py --years 2011,2018,2026  --limit-lots 50   # cheap demo
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
import time

import pandas as pd
import requests

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
IMGDIR = DATA / "facades"; IMGDIR.mkdir(parents=True, exist_ok=True)

SV_URL = "https://maps.googleapis.com/maps/api/streetview"
DEFAULT_YEARS = [2007, 2011, 2014, 2018, 2022, 2026]
SIZE = "640x400"
FOV = 80
PITCH = 5


def pick_panos_per_year(rows: pd.DataFrame, target_years: list[int]) -> pd.DataFrame:
    """For each (bbl, target_year) pick the pano whose year is closest, tie-break by month."""
    picks = []
    for bbl, group in rows.groupby("bbl"):
        g = group.dropna(subset=["pano_year"]).copy()
        if g.empty:
            continue
        g["pano_year"] = g["pano_year"].astype(int)
        for ty in target_years:
            g["_dist"] = (g["pano_year"] - ty).abs()
            g_sorted = g.sort_values(["_dist", "pano_date"], ascending=[True, False])
            best = g_sorted.iloc[0].copy()
            best["target_year"] = ty
            best["actual_year"] = int(best.pano_year)
            picks.append(best)
    df = pd.DataFrame(picks)
    return df.drop(columns=["_dist"], errors="ignore")


def fetch_one(session: requests.Session, api_key: str, pano_id: str, heading: float,
              out_path: pathlib.Path) -> tuple[bool, str]:
    if out_path.exists() and out_path.stat().st_size > 0:
        return True, "cached"
    params = {
        "size": SIZE,
        "pano": pano_id,
        "heading": f"{heading:.2f}",
        "fov": FOV,
        "pitch": PITCH,
        "key": api_key,
    }
    last_err = None
    for attempt in range(4):
        try:
            r = session.get(SV_URL, params=params, timeout=30)
            if r.status_code != 200:
                return False, f"http {r.status_code}"
            if len(r.content) < 5000:
                return False, "no imagery"
            out_path.write_bytes(r.content)
            return True, "downloaded"
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            last_err = e
            time.sleep(1.5 ** attempt)
    return False, f"network: {last_err}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=str, default=",".join(str(y) for y in DEFAULT_YEARS),
                    help="Comma-separated target years")
    ap.add_argument("--limit-lots", type=int, default=None,
                    help="Only process this many lots (for cheap demos)")
    args = ap.parse_args()

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        keyfile = pathlib.Path.home() / ".config" / "gmaps_api_key"
        if keyfile.exists():
            api_key = keyfile.read_text().strip()
    if not api_key:
        print("[!] No API key. Set GOOGLE_MAPS_API_KEY env var or write to ~/.config/gmaps_api_key")
        return 2

    target_years = [int(y) for y in args.years.split(",")]

    idx = pd.read_csv(DATA / "pano_index.csv")
    if args.limit_lots:
        keep_bbls = idx["bbl"].drop_duplicates().head(args.limit_lots)
        idx = idx[idx["bbl"].isin(keep_bbls)]
    print(f"[1] Loaded pano index: {len(idx)} rows, {idx.bbl.nunique()} lots")

    picks = pick_panos_per_year(idx, target_years)
    picks.to_csv(DATA / "fetch_plan.csv", index=False)
    print(f"[2] Fetch plan: {len(picks)} (bbl, year) pairs -> data/fetch_plan.csv")

    sess = requests.Session()
    ok = 0; skipped = 0; failed = 0
    for i, row in picks.iterrows():
        bbl_dir = IMGDIR / str(row.bbl); bbl_dir.mkdir(exist_ok=True)
        out = bbl_dir / f"{int(row.target_year):04d}_{row.actual_year}_{row.pano_date}.jpg"
        success, note = fetch_one(sess, api_key, row.pano_id, float(row.heading_deg), out)
        if success and note == "cached":
            skipped += 1
        elif success:
            ok += 1
        else:
            failed += 1
        if (i + 1) % 100 == 0:
            print(f"  ... {i+1}/{len(picks)}: {ok} new, {skipped} cached, {failed} failed")
        time.sleep(0.02)

    print(f"\n[3] Done. Downloaded: {ok}, Cached: {skipped}, Failed: {failed}")
    print(f"    Images written under {IMGDIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
