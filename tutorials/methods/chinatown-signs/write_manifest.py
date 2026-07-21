"""
Chinatown facades — Step 5: build a manifest that joins every downloaded image
back to its lot, address, PLUTO attributes, pano metadata, and comparison strip.

This is the "provenance is not optional" table for the temporal pipeline:
downstream OCR / color / embedding steps read this file and merge their outputs
onto it. Never fan-out to a subset of images without merging back.

Outputs:
  data/facades_manifest.csv       — one row per downloaded image
  data/facades_manifest.geojson   — same, geometry = pano capture location
  data/strips_manifest.csv        — one row per lot with strip path + n images
"""

from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
IMG_DIR = DATA / "facades"
STRIP_DIR = DATA / "strips"

# PLUTO columns to carry through to the manifest.
PLUTO_KEEP = [
    "bbl", "address", "bldgclass", "landuse", "yearbuilt",
    "numbldgs", "unitstotal", "unitsres",
]


def main() -> int:
    if not IMG_DIR.exists():
        print(f"[!] {IMG_DIR} does not exist. Run fetch_facades.py first.")
        return 1

    plan = pd.read_csv(DATA / "fetch_plan.csv")
    plan["bbl"] = plan["bbl"].astype(str)
    plan["target_year"] = plan["target_year"].astype(int)
    plan["actual_year"] = plan["actual_year"].astype(int)

    lots = pd.read_csv(DATA / "pluto_viewpoints.csv")
    lots["bbl"] = lots["bbl"].astype(str)
    lots = lots[PLUTO_KEEP + ["lot_lat", "lot_lon", "cam_to_lot_ft"]]

    rows = []
    for bbl_dir in sorted(IMG_DIR.iterdir()):
        if not bbl_dir.is_dir():
            continue
        for img in sorted(bbl_dir.glob("*.jpg")):
            parts = img.stem.split("_")
            if len(parts) < 3:
                continue
            try:
                target_year = int(parts[0])
                actual_year = int(parts[1])
            except ValueError:
                continue
            pano_date = "_".join(parts[2:])
            rows.append({
                "bbl": bbl_dir.name,
                "image_path": str(img.relative_to(HERE)),
                "target_year": target_year,
                "actual_year": actual_year,
                "pano_date": pano_date,
                "year_delta": actual_year - target_year,
            })
    imgs = pd.DataFrame(rows)
    print(f"[1] Found {len(imgs)} downloaded images across {imgs.bbl.nunique()} lots")

    m = imgs.merge(
        plan[["bbl", "target_year", "pano_id", "pano_lat", "pano_lon", "heading_deg"]],
        on=["bbl", "target_year"], how="left",
    ).merge(lots, on="bbl", how="left")

    strip_paths = {p.stem: str(p.relative_to(HERE)) for p in STRIP_DIR.glob("*.jpg")} \
        if STRIP_DIR.exists() else {}
    m["strip_path"] = m["bbl"].map(strip_paths).fillna("")

    m = m[[
        "bbl", "address", "image_path", "strip_path",
        "target_year", "actual_year", "year_delta", "pano_date",
        "pano_id", "pano_lat", "pano_lon", "heading_deg",
        "lot_lat", "lot_lon", "cam_to_lot_ft",
        "bldgclass", "landuse", "yearbuilt", "numbldgs", "unitstotal", "unitsres",
    ]]

    out_csv = DATA / "facades_manifest.csv"
    m.to_csv(out_csv, index=False)
    print(f"[2] Wrote {out_csv}  ({len(m)} rows)")

    features = []
    for _, r in m.iterrows():
        if pd.isna(r.pano_lat) or pd.isna(r.pano_lon):
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(r.pano_lon), float(r.pano_lat)]},
            "properties": {k: (None if pd.isna(v) else (v if isinstance(v, (int, float, str, bool)) else str(v)))
                           for k, v in r.to_dict().items()},
        })
    geo = {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "source": "Google Street View Static API via streetlevel (Time Machine)",
            "study_area": "Manhattan Chinatown, PLUTO tax lots within bbox 40.7128-40.7205, -74.003 to -73.9925",
            "note": "One feature per downloaded image. Geometry = pano capture location (where Google's car was). "
                    "Use lot_lat/lot_lon for tax-lot-based joins.",
        },
    }
    out_geo = DATA / "facades_manifest.geojson"
    out_geo.write_text(json.dumps(geo))
    print(f"[3] Wrote {out_geo}  ({len(features)} features)")

    strips = (
        m.groupby(["bbl", "address", "strip_path", "lot_lat", "lot_lon"])
        .agg(n_images=("image_path", "count"),
             years=("actual_year", lambda s: ",".join(sorted({str(y) for y in s}))),
             earliest=("actual_year", "min"),
             latest=("actual_year", "max"))
        .reset_index()
    )
    strips["span_years"] = strips["latest"] - strips["earliest"]
    out_strips = DATA / "strips_manifest.csv"
    strips.to_csv(out_strips, index=False)
    print(f"[4] Wrote {out_strips}  ({len(strips)} lots)")

    print("\n[5] Sample manifest rows:")
    print(m.head(3).to_string(index=False, max_colwidth=30))
    return 0


if __name__ == "__main__":
    sys.exit(main())
