"""
Chinatown facades — Step 1: PLUTO lots -> facade-facing Street View viewpoints.

For each tax lot in the study area, compute:
  - a camera position on the nearest street
  - a camera heading pointing from the street toward the lot centroid

Outputs data/pluto_viewpoints.csv (one row per lot).

Companion to README.md, "PLUTO + temporal Street View" section.
"""

from __future__ import annotations

import math
import pathlib
import sys

import io
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import nearest_points

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"; DATA.mkdir(exist_ok=True)

# Manhattan Chinatown: North, South, East, West.
BBOX = (40.7205, 40.7128, -73.9925, -74.0030)
N, S, E, W = BBOX

PLUTO_URL = (
    "https://data.cityofnewyork.us/resource/64uk-42ks.csv"
    "?$select=bbl,address,bldgclass,landuse,yearbuilt,numbldgs,unitstotal,unitsres,"
    "lotfront,lotdepth,bldgfront,bldgdepth,latitude,longitude,zipcode,"
    "assesstot,builtfar,histdist"
    f"&$where=latitude between {S} and {N} and longitude between {W} and {E} and borough='MN'"
    "&$limit=50000"
)


def bearing_deg(lat1, lon1, lat2, lon2) -> float:
    """Bearing from point 1 to point 2, degrees CW from north."""
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def main() -> int:
    print(f"[1] Pulling PLUTO lots in bbox {BBOX} ...")
    r = requests.get(PLUTO_URL, timeout=60); r.raise_for_status()
    pluto = pd.read_csv(io.StringIO(r.text))
    print(f"    {len(pluto)} lots")
    pluto = pluto.dropna(subset=["latitude", "longitude"]).copy()
    pluto["bbl"] = pluto["bbl"].astype(str).str.rstrip("0").str.rstrip(".")

    print(f"[2] Pulling OSM walk-network streets in bbox ...")
    G = ox.graph_from_bbox(bbox=(W, S, E, N), network_type="walk", simplify=True)
    edges = ox.graph_to_gdfs(G, nodes=False)[["geometry"]].to_crs(4326)
    print(f"    {len(edges)} street edges")

    # Reproject to a metric CRS for nearest-line + distance math.
    METRIC = "EPSG:2263"  # NAD83 / NY Long Island (ftUS)
    edges_m = edges.to_crs(METRIC)
    edge_geoms = list(edges_m.geometry.values)

    lots_gdf = gpd.GeoDataFrame(
        pluto,
        geometry=gpd.points_from_xy(pluto.longitude, pluto.latitude),
        crs=4326,
    ).to_crs(METRIC)

    print(f"[3] Computing facade viewpoints ...")
    OFFSET_FT = 5.0  # step camera a hair into the street to avoid landing on the sidewalk curb
    rows = []
    edges_sindex = edges_m.sindex

    for _, lot in lots_gdf.iterrows():
        p = lot.geometry
        # sindex.nearest returns array shape (2, k): [query_ix row, tree_ix row]
        idxs = edges_sindex.nearest(p, return_all=False)
        tree_idx = int(idxs[1][0])
        best = edge_geoms[tree_idx]
        _, best_nearest = nearest_points(p, best)
        best_d = p.distance(best_nearest)

        # Step slightly toward the street centerline: interp between p and nearest point on the street
        # by (OFFSET_FT / distance). Then use that as the camera position.
        if best_d < 1:
            cam = best_nearest
        else:
            frac = min(1.0, (best_d - OFFSET_FT) / best_d) if best_d > OFFSET_FT else 0.0
            cam_x = p.x + (best_nearest.x - p.x) * (1 - (1 - frac))
            cam_y = p.y + (best_nearest.y - p.y) * (1 - (1 - frac))
            cam = Point(cam_x, cam_y)

        cam_ll = gpd.GeoSeries([cam], crs=METRIC).to_crs(4326).iloc[0]
        lot_ll_pt = gpd.GeoSeries([p], crs=METRIC).to_crs(4326).iloc[0]

        heading = bearing_deg(cam_ll.y, cam_ll.x, lot_ll_pt.y, lot_ll_pt.x)

        rows.append({
            "bbl": lot["bbl"],
            "address": lot.get("address", ""),
            "bldgclass": lot.get("bldgclass", ""),
            "landuse": lot.get("landuse", ""),
            "yearbuilt": lot.get("yearbuilt", ""),
            "numbldgs": lot.get("numbldgs", ""),
            "unitstotal": lot.get("unitstotal", ""),
            "unitsres": lot.get("unitsres", ""),
            "lot_lat": lot_ll_pt.y,
            "lot_lon": lot_ll_pt.x,
            "cam_lat": cam_ll.y,
            "cam_lon": cam_ll.x,
            "cam_to_lot_ft": round(float(best_d), 2),
            "heading_deg": round(heading, 2),
        })

    df = pd.DataFrame(rows)
    out = DATA / "pluto_viewpoints.csv"
    df.to_csv(out, index=False)
    print(f"[4] Wrote {out}: {len(df)} viewpoints")

    print("\n[4] Sample:")
    print(df.head(6).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
