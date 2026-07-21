"""
Chinatown facades — Step 2: enumerate current + historical Google Street View panos
at each lot's camera position, using the `streetlevel` library.

Reads data/pluto_viewpoints.csv, writes data/pano_index.csv (many rows per lot,
one per historical capture).

Runtime: ~0.3-0.6s per lot lookup. On 1,026 lots that is ~5-10 minutes.
Use LIMIT below during development to sample a smaller batch first.
"""

from __future__ import annotations

import math
import pathlib
import sys
import time

import pandas as pd
from streetlevel import streetview

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"

LIMIT = None   # e.g. 40 for a quick smoke test; None = all
SEARCH_RADIUS_M = 25


def bearing_deg(lat1, lon1, lat2, lon2) -> float:
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def main() -> int:
    vp = pd.read_csv(DATA / "pluto_viewpoints.csv")
    if LIMIT:
        vp = vp.head(LIMIT).copy()
    print(f"[1] Loaded {len(vp)} viewpoints")

    rows = []
    misses = 0
    for i, v in vp.iterrows():
        try:
            pano = streetview.find_panorama(v.cam_lat, v.cam_lon, radius=SEARCH_RADIUS_M)
        except Exception as e:
            misses += 1
            print(f"  [!] {v.bbl}: streetlevel error {e}")
            continue
        if pano is None:
            misses += 1
            continue

        panos = [pano] + list(pano.historical or [])
        for p in panos:
            # heading FROM this specific pano's actual location TO the lot centroid
            heading = bearing_deg(p.lat, p.lon, v.lot_lat, v.lot_lon)
            date_str = f"{p.date.year:04d}-{p.date.month:02d}" if p.date else ""
            year = p.date.year if p.date else None
            rows.append({
                "bbl": v.bbl,
                "address": v.address,
                "pano_id": p.id,
                "pano_date": date_str,
                "pano_year": year,
                "pano_lat": p.lat,
                "pano_lon": p.lon,
                "lot_lat": v.lot_lat,
                "lot_lon": v.lot_lon,
                "heading_deg": round(heading, 2),
                "cam_to_lot_ft": v.cam_to_lot_ft,
            })

        if (i + 1) % 50 == 0:
            print(f"  ... {i+1}/{len(vp)} lots, {len(rows)} pano entries so far, {misses} misses")

    df = pd.DataFrame(rows)
    df.to_csv(DATA / "pano_index.csv", index=False)
    print(f"[2] Wrote {DATA/'pano_index.csv'}: {len(df)} rows across {df.bbl.nunique()} lots")
    print(f"    Lots with no coverage: {misses}")

    if len(df):
        print("\n[3] Year distribution:")
        print(df.groupby("pano_year").size().rename("n_panos"))
        print("\n[3] Panos per lot (histogram):")
        print(df.groupby("bbl").size().describe().round(1))

    return 0


if __name__ == "__main__":
    sys.exit(main())
