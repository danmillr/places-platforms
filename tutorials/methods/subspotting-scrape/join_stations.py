"""
Join the Subspotting long-format CSV to real MTA station coordinates,
producing a GeoJSON of stations with per-carrier reception attributes.

Runs after scrape.py. Companion to README.md, step 7.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd
import requests

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"

STATIONS_URL = "https://data.ny.gov/resource/39hk-dx4f.csv?$limit=1000"

# For lines whose gtfs_stop_id sort does NOT produce the physical station order
# (because the route shares track with other lines and takes on their stop_id
# prefixes), we hard-code the ordered stop_ids from the Subspotting mile-0
# terminal outward. Ground-truthed against the MTA subway map.
MANUAL_ORDER: dict[str, list[str]] = {
    # G: Court Sq -> Church Av (Queens to Brooklyn)
    "G": ["G22", "G24", "G26", "G28", "G29", "G30", "G31", "G32", "G33", "G34",
          "G35", "G36", "A42", "F20", "F21", "F22", "F23", "F24", "F25", "F26", "F27"],
    # A: Inwood 207 St -> Far Rockaway (via express Manhattan then Brooklyn/Queens)
    "A": ["A02", "A03", "A05", "A06", "A07", "A09", "A10", "A11", "A12", "A14",
          "A15", "A16", "A17", "A18", "A19", "A20", "A21", "A22", "A24", "A25",
          "A27", "A28", "A30", "A31", "A32", "A33", "A34", "A36", "A38", "A40",
          "A41", "A42", "A43", "A44", "A45", "A46", "A47", "A48", "A49", "A50",
          "A51", "A52", "A53", "A54", "A55", "A57", "A59", "A60", "A61", "A63",
          "A64", "A65", "H01", "H02", "H03", "H04", "H06", "H07", "H08", "H09",
          "H10", "H11"],
    # C: 168 St -> Euclid Av (Manhattan through Brooklyn)
    "C": ["A09", "A10", "A11", "A12", "A14", "A15", "A16", "A17", "A18", "A19",
          "A20", "A21", "A22", "A24", "A25", "A27", "A28", "A30", "A31", "A32",
          "A33", "A34", "A36", "A38", "A40", "A41", "A42", "A43", "A44", "A45",
          "A46", "A47", "A48", "A49", "A50", "A51", "A52", "A53", "A54", "A55"],
    # E: Jamaica Center -> World Trade Center
    "E": ["G05", "G06", "G07", "G08", "G09", "G10", "G11", "G12", "G13", "G14",
          "F09", "F11", "F12", "D14", "D15", "F14", "F15", "F16", "A25", "A27",
          "A28", "A30", "A31", "A32", "A33", "A34", "E01"],
    # B: Bedford Park -> Brighton Beach (via Manhattan)
    "B": ["D01", "D03", "D04", "D05", "D06", "D07", "D08", "D09", "D10", "D11",
          "D12", "D13", "A24", "D14", "D15", "D16", "D17", "D18", "D19", "D20",
          "D21", "D22", "D24", "D25", "D26", "D27", "D28", "D29", "D30", "D31",
          "D32", "D33", "D34", "D35", "D40", "D41", "D42", "D43"],
    # D: Norwood-205 -> Coney Island (via Manhattan express)
    "D": ["D01", "D03", "D04", "D05", "D06", "D07", "D08", "D09", "D10", "D11",
          "D12", "D13", "A24", "D14", "D15", "D16", "D17", "D18", "D19", "D20",
          "D21", "D22", "D24", "D25", "D26", "D27", "D28", "D29", "N04", "N05",
          "N06", "B12", "B13", "B14", "B15", "B16", "B17", "B18", "B19", "B20",
          "B21", "B22", "B23"],
    # F: Jamaica-179 -> Coney Island
    "F": ["F01", "F02", "F03", "F04", "F05", "F06", "F07", "G14", "F09", "F11",
          "F12", "D14", "D15", "F14", "F15", "F16", "D17", "D18", "D19", "D20",
          "D21", "A32", "F18", "F20", "F21", "F22", "F23", "F24", "F25", "F26",
          "F27", "F29", "F30", "F31", "F32", "F33", "F34", "F35", "F36", "F38",
          "F39", "F40", "B23"],
    # M: Middle Village -> Forest Hills-71 Av (rush hour to Metropolitan Ave)
    "M": ["M01", "M04", "M05", "M06", "M08", "M09", "M10", "M11", "M12", "M13",
          "M14", "M16", "M18", "M19", "M20", "M21", "M22", "M23", "D18", "D19",
          "D20", "D21", "A32", "F18", "F20", "F21", "F22", "F23", "F24", "F25",
          "F26", "F27"],
    # J: Jamaica Center -> Broad St
    "J": ["J12", "J13", "J14", "J15", "J16", "J17", "J19", "J20", "J21", "J22",
          "J23", "J24", "J27", "J28", "J29", "J30", "J31", "M11", "M12", "M13",
          "M14", "M16", "M18", "M19", "M20", "M21", "M22", "M23", "M01"],
    # Z: same as J but express (weekday peak)
    "Z": ["J12", "J13", "J14", "J15", "J16", "J17", "J19", "J20", "J21", "J22",
          "J23", "J24", "J27", "J28", "J29", "J30", "J31", "M11", "M12", "M13",
          "M14", "M16", "M18", "M19", "M20", "M21", "M22", "M23", "M01"],
    # N: Astoria-Ditmars -> Coney Island (via Manhattan and Sea Beach)
    "N": ["R01", "R03", "R04", "R05", "R06", "R08", "R09", "R11", "R13", "R14",
          "R15", "R16", "R17", "R18", "R19", "R20", "R21", "R22", "R23", "R24",
          "R25", "R27", "R28", "R30", "R31", "R32", "R33", "N02", "N03", "N04",
          "N05", "N06", "N07", "N08", "N09", "N10", "B12", "B13", "B14", "B15",
          "B16", "B17", "B18", "B19", "B20", "B21", "B22", "B23"],
    # Q: 96 St -> Coney Island (via Brighton)
    "Q": ["Q05", "Q04", "Q03", "R14", "R15", "R16", "R17", "R18", "R19", "R20",
          "R21", "R22", "R23", "R24", "R25", "R27", "R28", "R30", "R31", "R32",
          "D24", "D25", "D26", "D27", "D28", "D29", "D30", "D31", "D32", "D33",
          "D34", "D35", "D40", "D41", "D42", "D43", "B14", "B15", "B16", "B17",
          "B18", "B19", "B20", "B21", "B22", "B23"],
    # R: Forest Hills-71 Av -> Bay Ridge-95 St
    "R": ["G14", "F09", "F11", "F12", "R01", "R03", "R04", "R05", "R06", "R08",
          "R09", "R11", "R13", "R14", "R15", "R16", "R17", "R18", "R19", "R20",
          "R21", "R22", "R23", "R24", "R25", "R27", "R28", "R30", "R31", "R32",
          "R33", "R36", "R39", "R40", "R41", "R42", "R43", "R44", "R45"],
}


def geodesic_mi(lat1, lon1, lat2, lon2):
    R_mi = 3958.7613
    lat1r, lat2r = np.radians(lat1), np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon/2)**2
    return 2 * R_mi * np.arcsin(np.sqrt(a))


def build_station_order(stations: pd.DataFrame) -> pd.DataFrame:
    """For each of the 21 Subspotting lines, return an ordered station DataFrame
    with columns [line, stop_id, stop_name, lat, lon, mile_cum]."""
    rows = []
    for line in ["1","2","3","4","5","6","7","A","C","E","B","D","F","M","G",
                 "J","Z","L","N","Q","R"]:
        if line in MANUAL_ORDER:
            wanted = MANUAL_ORDER[line]
            sub = stations[stations["gtfs_stop_id"].isin(wanted)].copy()
            sub["_ord"] = sub["gtfs_stop_id"].map({sid: i for i, sid in enumerate(wanted)})
            sub = sub.sort_values("_ord")
        else:
            m = stations["daytime_routes"].fillna("").str.split().apply(lambda xs: line in xs)
            sub = stations[m].sort_values("gtfs_stop_id").copy()
        sub = sub.drop_duplicates("gtfs_stop_id").reset_index(drop=True)

        if sub.empty:
            print(f"[!] No stops found for line {line}")
            continue

        lats = sub["gtfs_latitude"].values
        lons = sub["gtfs_longitude"].values
        seg = geodesic_mi(lats[:-1], lons[:-1], lats[1:], lons[1:])
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        sub["mile_cum"] = cum

        for _, r in sub.iterrows():
            rows.append({
                "line": line,
                "stop_id": r["gtfs_stop_id"],
                "stop_name": r["stop_name"],
                "borough": r["borough"],
                "structure": r["structure"],
                "lat": r["gtfs_latitude"],
                "lon": r["gtfs_longitude"],
                "mile_cum": round(float(r["mile_cum"]), 3),
            })

    return pd.DataFrame(rows)


def snap_to_stations(long: pd.DataFrame, ordered: pd.DataFrame) -> pd.DataFrame:
    """Aggregate long-format samples up to the nearest station along each line."""
    out = []
    for line, line_samples in long.groupby("line"):
        stops = ordered[ordered["line"] == line].sort_values("mile_cum").reset_index(drop=True)
        if stops.empty:
            continue
        mile_arr = stops["mile_cum"].values
        for _, s in line_samples.iterrows():
            idx = int(np.argmin(np.abs(mile_arr - s["mile_from_terminal"])))
            out.append({
                "line": line,
                "stop_id": stops.loc[idx, "stop_id"],
                "stop_name": stops.loc[idx, "stop_name"],
                "lat": stops.loc[idx, "lat"],
                "lon": stops.loc[idx, "lon"],
                "structure": stops.loc[idx, "structure"],
                "borough": stops.loc[idx, "borough"],
                "carrier": s["carrier"],
                "has_reception": s["has_reception"],
                "score": s["score"],
            })
    return pd.DataFrame(out)


def main() -> int:
    long = pd.read_csv(DATA / "subspotting_long.csv")
    print(f"[a] Loaded long CSV: {len(long)} rows")

    print(f"[b] Fetching MTA stations from {STATIONS_URL}")
    stations = pd.read_csv(STATIONS_URL)
    print(f"    Got {len(stations)} station rows")

    ordered = build_station_order(stations)
    ordered.to_csv(DATA / "stations_ordered.csv", index=False)
    print(f"[c] Ordered stations per line: {len(ordered)} rows -> stations_ordered.csv")

    snapped = snap_to_stations(long, ordered)
    per_station = (
        snapped
        .groupby(["line", "stop_id", "stop_name", "lat", "lon", "structure", "borough", "carrier"])
        .agg(reception_frac=("has_reception", "mean"),
             mean_score=("score", "mean"),
             n_samples=("has_reception", "size"))
        .reset_index()
    )
    per_station["reception_frac"] = per_station["reception_frac"].round(3)
    per_station["mean_score"] = per_station["mean_score"].round(4)

    wide = per_station.pivot_table(
        index=["line","stop_id","stop_name","lat","lon","structure","borough"],
        columns="carrier",
        values="reception_frac",
        fill_value=0.0,
    ).reset_index()
    wide.columns.name = None
    wide.to_csv(DATA / "stations_reception.csv", index=False)
    print(f"[d] Per-station reception CSV: {len(wide)} rows -> stations_reception.csv")

    features = []
    for _, r in wide.iterrows():
        props = {
            "line": r["line"],
            "stop_id": r["stop_id"],
            "stop_name": r["stop_name"],
            "borough": r["borough"],
            "structure": r["structure"],
        }
        for c in ["att","tmobile","verizon","sprint"]:
            props[f"{c}_reception_frac"] = float(r.get(c, 0.0))
        any_reception = any(props[f"{c}_reception_frac"] > 0.5 for c in ["att","tmobile","verizon","sprint"])
        n_carriers = sum(1 for c in ["att","tmobile","verizon","sprint"] if props[f"{c}_reception_frac"] > 0.5)
        props["n_carriers_majority"] = n_carriers
        props["any_majority_reception"] = any_reception
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(r["lon"]), float(r["lat"])]},
            "properties": props,
        })
    geo = {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "source": "Subspotting.nyc System Explorer PNG (2017-01)",
            "note": "Reception values are the mean fraction of samples in the Subspotting artifact "
                    "within +/- 0.1 mile of each MTA station where the given carrier's color was "
                    "present. Values close to 0 mean no reception at that station in the 2017 artifact.",
        },
    }
    (DATA / "stations_reception.geojson").write_text(json.dumps(geo, indent=1))
    print(f"[e] GeoJSON: {len(features)} station features -> stations_reception.geojson")

    print("\n[e] Sample: top 5 best-covered stations (by n_carriers with majority reception):")
    top = wide.copy()
    top["n_carriers"] = sum((top[c] > 0.5).astype(int) for c in ["att","tmobile","verizon","sprint"])
    print(top.sort_values(["n_carriers","tmobile"], ascending=False).head(10)[
        ["line","stop_name","borough","structure","att","tmobile","verizon","sprint","n_carriers"]
    ].to_string(index=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
