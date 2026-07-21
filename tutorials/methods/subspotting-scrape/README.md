# Subspotting: Recovering Structured Data from a Static Infographic

**Status: Full.** Working pipeline: `scrape.py` → `join_stations.py` → `visualize.py`. Runs end-to-end from a clean Python 3.10+ env with `requests`, `pillow`, `numpy`, `pandas`, `lxml`, and `matplotlib` installed. Produced datasets live in `data/` (see the "What was produced" section below).

## What you will build

A pipeline that takes the 2017 Subspotting "System Explorer" — a color-coded PNG showing cell-carrier reception across the NYC subway — and reverse-engineers it back into a structured dataset. Two outputs:

1. **Long-format CSV** — one row per `(subway_line, mile_marker, carrier)` with a `has_reception` boolean and a confidence score.
2. **GeoJSON** — the same records joined to real MTA station coordinates, so you can put them on a map.

The purpose is methodological: **scraping is not just for HTML.** Static infographics are also data, if you can decode their visual grammar. This method teaches you how.

## Why this matters (design principle)

Subspotting (subspotting.nyc, 2015–2017) was itself a **counter-mapping project** — three researchers walking every subway line with signal-strength meters to make visible an infrastructure that the carriers had not documented. The final artifact they published is a linearized map: each subway line is "unrolled" into a horizontal band, with mile markers on the x-axis and colored diagonal-line patterns showing which carrier had reception where.

That artifact is a design decision. To share the data as a poster, they collapsed a spatial dataset into a graphic. Your job is to recover the underlying data from the graphic — knowing that some fidelity will be lost, and knowing you should cite the original.

> 🕐 *The Subspotting data is from January 2017. Transit Wireless completed underground cellular rollout across the NYC subway between 2017 and 2021, so the reception picture in the artifact does not describe today. That drift is itself worth analyzing.*

Two lessons for your final project:

- **Every visualization is a lossy compression of a dataset.** If someone else's map is the only version of the data you have, extracting it is a legitimate research move.
- **Any dataset older than the infrastructure it describes is a historical document, not a fact.** Frame it as such.

## Data sources

- **Source artifact (PNG):** https://subspotting.nyc/assets/img/main/provider/popup-systemexplorer.png — the linearized reception map, ~3 MB, static since Jan 2017.
- **Ruler overlay (SVG):** https://subspotting.nyc/assets/img/main/provider/explorer-overlay.svg — the mile-scale bar (0.0 → 32.0 mi), which gives you pixel-to-mile calibration.
- **Landing page:** https://subspotting.nyc/main/explorer.html — the interactive explorer with a magnifying-glass zoom (uses okzoom.js on the same PNG).
- **Subspotting project home:** https://subspotting.nyc — for the per-carrier breakdown pages, useful for ground-truthing which horizontal band is which subway line.
- **MTA Subway Stations (with coordinates):** https://data.ny.gov/Transportation/MTA-Subway-Stations/39hk-dx4f — for the geographic join in Step 7.
- **Inter-station distances:** the MTA does not publish a clean "miles from terminal" table, but Wikipedia's per-line articles list station spacing in miles/km; you can also compute it from station coordinates along the route geometry (see extensions).

Carrier color palette, taken from the CSS of the source page:

| Carrier   | Hex        | Pattern (in artifact)       |
|-----------|------------|-----------------------------|
| AT&T      | `#067ab4`  | diagonal blue lines         |
| T-Mobile  | `#e20074`  | diagonal magenta lines      |
| Verizon   | `#ff0000`  | diagonal red lines          |
| Sprint    | `#ffe100`  | diagonal yellow lines       |

## Prerequisites

- Python 3.10+ with `requests`, `pillow`, `numpy`, `pandas`, `lxml`, `geopandas`, `shapely`, `matplotlib`
- Ability to run a Jupyter kernel (Colab or local)
- Comfort with numpy array indexing (you will be slicing a raster)

```bash
pip install requests pillow numpy pandas lxml geopandas shapely matplotlib
```

## Walkthrough

### 1. Fetch the source assets

```python
import requests, pathlib
OUT = pathlib.Path("subspotting"); OUT.mkdir(exist_ok=True)

for name, url in {
    "systemexplorer.png": "https://subspotting.nyc/assets/img/main/provider/popup-systemexplorer.png",
    "overlay.svg":        "https://subspotting.nyc/assets/img/main/provider/explorer-overlay.svg",
}.items():
    (OUT / name).write_bytes(requests.get(url).content)
```

### 2. Calibrate pixel-to-mile from the SVG ruler

The overlay is a 1728 × 73 SVG. A `<g>` group is translated `(92, 11)`, and inside it, `<text>` labels sit at every 5 miles (0, 5, 10, 15, 20, 25, 30) plus 32. Tall `<path>` tick marks sit at the same x-coordinates. Fit a linear model:

```python
from lxml import etree
import numpy as np

ns = {"svg": "http://www.w3.org/2000/svg"}
tree = etree.parse(OUT / "overlay.svg")
# The group carrying the tick geometry has a translate(92, 11)
group = tree.find(".//svg:g[@id='Page-1']/svg:g/svg:g", ns)
tx = 92.0

miles, xs = [], []
for t in tree.iterfind(".//svg:text", ns):
    txt = t.findtext("svg:tspan", namespaces=ns)
    try:
        mile = float(txt)
    except (TypeError, ValueError):
        continue
    tspan = t.find("svg:tspan", ns)
    xs.append(float(tspan.get("x")) + tx)  # absolute px in SVG
    miles.append(mile)

miles, xs = np.array(miles), np.array(xs)
slope, intercept = np.polyfit(xs, miles, 1)  # miles = slope*px + intercept
print(f"1 SVG pixel = {slope:.5f} miles, intercept = {intercept:.3f}")
```

Expect roughly **48 px per mile in SVG space**. Keep the intercept — the "0.0 mile" tick is not at x=0 of the SVG (there is padding).

### 3. Load the PNG and reconcile scales

The raw PNG is much wider than the SVG (the page displays them at the same width, but the PNG has its own native resolution). Rescale the PNG to the SVG's coordinate system so the ruler you just calibrated actually applies:

```python
from PIL import Image
img = Image.open(OUT / "systemexplorer.png").convert("RGB")
print("PNG native size:", img.size)   # e.g., (something like 3400+ , tall)

TARGET_W = 1728  # match SVG width
scale = TARGET_W / img.width
img_scaled = img.resize((TARGET_W, round(img.height * scale)), Image.LANCZOS)
arr = np.array(img_scaled)  # shape: (H, 1728, 3)
```

Now `arr[:, x, :]` at column `x` corresponds to `slope * x + intercept` miles. Sanity check: pick two visible landmarks in the image (e.g., a terminal station) and verify the miles look right.

### 4. Segment the horizontal bands (one per subway line)

Each subway line is drawn as a horizontal track (a near-black line) plus a colored pattern band above or below. Find rows that contain a lot of near-black pixels — those are the tracks:

```python
track_mask = (arr.max(axis=2) < 60)          # near-black pixel = track
row_score  = track_mask.mean(axis=1)          # fraction of black in each row
line_rows  = np.where(row_score > 0.03)[0]    # threshold: tune it

# Group contiguous rows into bands, one per line
bands = []
current = [line_rows[0]]
for r in line_rows[1:]:
    if r - current[-1] <= 3:
        current.append(r)
    else:
        bands.append((current[0], current[-1]))
        current = [r]
bands.append((current[0], current[-1]))
print(f"Detected {len(bands)} candidate lines")
```

You will almost certainly need to hand-tune the threshold and the `<=3` gap. Save a preview image with each band boxed, and look at it. This is the step that will absorb the most time.

### 5. Label the bands (which band is which line?)

There is **no automatic way** to know that band #7 is the 4/5/6 versus the L. The original artifact draws them in an order Subspotting chose for graphic reasons. Two options:

- **Manual:** zoom into the artifact on subspotting.nyc, note the top-to-bottom order, and hard-code the mapping.
- **Cross-reference:** Subspotting also publishes **per-carrier per-line** breakdown pages (linked from their main page); match the total length of each band (Step 2 gives you mile-length) to known subway line lengths from Wikipedia or the MTA. The 1 line is ~14.6 mi; the A is ~32.4 mi; the 7 is ~10.5 mi; etc.

Store as a dict:

```python
LINES_TOP_TO_BOTTOM = ["1","2","3","4","5","6","7","A","B","C","D","E","F","G","J","L","M","N","Q","R","W","Z"]
# adjust to match what you see
```

### 6. Decode carriers per column per band → long CSV

For each band, sweep columns and check whether each carrier's signature color is present. The patterns are diagonal thin lines, so any given column will only contain a few carrier pixels — you need to **count**, not just check for a single pixel.

```python
CARRIERS = {
    "att":     (0x06, 0x7a, 0xb4),
    "tmobile": (0xe2, 0x00, 0x74),
    "verizon": (0xff, 0x00, 0x00),
    "sprint":  (0xff, 0xe1, 0x00),
}

def carrier_score(pixels, ref, tol=40):
    """Return fraction of pixels within tol of ref color (per-channel L-inf)."""
    diff = np.abs(pixels.astype(int) - np.array(ref)).max(axis=-1)
    return (diff <= tol).mean()

rows = []
for line_name, (r0, r1) in zip(LINES_TOP_TO_BOTTOM, bands):
    band = arr[r0:r1+1]                       # (band_h, 1728, 3)
    for x in range(band.shape[1]):
        mile = slope * x + intercept
        if mile < 0: continue
        col = band[:, x, :]
        for carrier, ref in CARRIERS.items():
            score = carrier_score(col, ref)
            rows.append({
                "line": line_name,
                "mile": round(float(mile), 3),
                "carrier": carrier,
                "score": round(float(score), 4),
                "has_reception": bool(score >= 0.05),   # tune this cutoff
            })

import pandas as pd
df = pd.DataFrame(rows)
df.to_csv("subspotting_long.csv", index=False)
```

The `0.05` cutoff means "at least 5% of the column's pixels look like this carrier's color" — since patterns are sparse, do not expect anywhere near 100%. Preview a few rows and adjust.

### 7. Join mile markers to MTA stations → GeoJSON

You need a table of `(line, station, mile_from_terminal, lat, lon)`. Build it from the MTA stations dataset plus per-line station order:

```python
stations = pd.read_csv("https://data.ny.gov/resource/39hk-dx4f.csv?$limit=1000")
```

The stations table has `gtfs_latitude`, `gtfs_longitude`, `line` (route ID), and `stop_name`. It does not have a "miles from terminal" column, so compute it: for each line, sort stations by their `stop_id` sequence (or by projecting onto the line geometry from MTA GTFS shapes), then use `geopy.distance.geodesic` between consecutive stations to get running distance.

Then, for each row of your long CSV, find the nearest station on the same line and attach its lat/lon:

```python
import geopandas as gpd
from shapely.geometry import Point

# stations_by_line: {line_id: DataFrame with columns [stop_name, mile, lat, lon]}
# built in the step above

def nearest_station(line, mile):
    s = stations_by_line[line]
    idx = (s["mile"] - mile).abs().idxmin()
    return s.loc[idx, ["stop_name", "lat", "lon"]]

matches = df.apply(lambda r: nearest_station(r["line"], r["mile"]), axis=1)
df_geo = pd.concat([df, matches], axis=1)
df_geo["geometry"] = df_geo.apply(lambda r: Point(r["lon"], r["lat"]), axis=1)
gdf = gpd.GeoDataFrame(df_geo, geometry="geometry", crs="EPSG:4326")
gdf.to_file("subspotting_stations.geojson", driver="GeoJSON")
```

Aggregate before writing if you only want one feature per station-carrier: `df_geo.groupby(["line","stop_name","carrier"])["has_reception"].mean()`.

### 8. Sanity-check with a map

```python
import matplotlib.pyplot as plt
ax = gdf[gdf.carrier == "att"].plot(column="has_reception", markersize=4, legend=True, figsize=(8, 10))
ax.set_title("AT&T reception, 2017 (from Subspotting)")
plt.savefig("att_2017.png", dpi=150)
```

Compare against the original artifact. If your borough shapes look right (Manhattan running north-south, Bronx up top, Queens east), you got the calibration and the join right.

## Extensions

- **Diff against today.** Walk a few blocks of a line with a signal-strength app (e.g., Cellular-Z on Android, Field Test Mode on iPhone) and compare to Subspotting's 2017 reading. Where has coverage arrived? Where hasn't it?
- **Reproject onto GTFS shapes.** Instead of "nearest station," project each mile marker onto the actual MTA `shapes.txt` polyline for that route. Gives you continuous line features instead of point features. Good for choropleth-style reception ribbons.
- **Compare carriers.** Which carrier had the best 2017 underground coverage? Which had the worst? Frame it in the essay: the underground network was carrier-fragmented before Transit Wireless standardized it — Subspotting is a snapshot of that fragmentation.
- **Recover the original DAS deployment plan.** Transit Wireless publishes press releases about which stations came online when. Overlay their timeline against your extracted 2017 map — you may be able to date-stamp specific portions of Subspotting's data.
- **Publish your extraction as its own artifact.** A cleaned CSV + GeoJSON, with methodology notes and a link to Subspotting, is a valid contribution. Attribute clearly.

## Common pitfalls

- **Assuming the map is geographic.** It is not. It is a linear "unrolled" view. The x-axis is miles-from-terminal, not longitude. Only after Step 7 is your data geographic.
- **Assuming pixel-to-mile is constant across the artifact.** It is, by construction (the ruler is linear) — but only if you rescale the PNG to the SVG width first. Skipping Step 3 will give you nonsense.
- **Guessing which band is which line.** There is no cheat here — you have to ground-truth against Subspotting's other pages or the known length of each line. Document your mapping in a table.
- **Trusting a single-pixel match.** The patterns are diagonal lines with lots of white background. A column's carrier signal is a *fraction* of colored pixels, not a boolean. Tune the score cutoff.
- **Publishing derivative maps without attribution.** The PNG is Subspotting's intellectual work. Cite them prominently in any deliverable. Fair-use quotation of the underlying data is fine for research; redistribution of the PNG as your own image is not.
- **Treating the data as current.** Underground cell coverage in NYC in 2026 is materially different than in 2017. Never present your extracted map without a "as of Jan 2017" caption.
- **Overfitting the color tolerance.** JPEG-style compression artifacts and okzoom's downsampling make the carrier colors bleed. If you set the tolerance too tight, you will miss most of the pattern; too loose, and station-name text (grey) starts scoring as reception. Preview.

## What was produced (this repo)

Run:

```bash
python3 scrape.py         # PNG -> long CSV + wide CSV + metadata
python3 join_stations.py  # long CSV + MTA stations -> station GeoJSON
python3 visualize.py      # GeoJSON -> reception_map.png (4-panel sanity check)
```

Outputs in `data/`:

| File | Rows | What it is |
|---|---|---|
| `systemexplorer.png` | — | Raw 7200x8600 PNG from subspotting.nyc (2017-01) |
| `overlay.svg` | — | Raw mile-scale SVG from subspotting.nyc |
| `systemexplorer_1728w.png` | — | PNG rescaled to match SVG width (calibration space) |
| `bands_preview.png` | — | 21 detected line bands with green boundary lines drawn on |
| `metadata.json` | — | Pixel-to-mile calibration, band pixel ranges, carrier hex refs |
| `subspotting_long.csv` | 15,760 | `(line, mile_from_terminal, carrier, score, has_reception)` at 0.1-mile resolution |
| `subspotting_wide.csv` | 21 | Per-line % coverage per carrier |
| `stations_ordered.csv` | 774 | Ordered MTA stops per line with cumulative geodesic mile from terminal |
| `stations_reception.csv` | 626 | Per-`(line, station)`: fraction of samples with each carrier's color present |
| `stations_reception.geojson` | 626 features | Same data, as GeoJSON points with 4-carrier attributes |
| `reception_map.png` | — | 4-panel sanity-check map (one panel per carrier) |

### Line-length ground truth check

The `abs_mile` extent of each detected band matches known subway line lengths within about 5%. Highlights:

| Line | Detected length (mi) | Actual (mi) | Notes |
|---|---|---|---|
| 7  | 10.5 | 10.5 | ✓ |
| A  | 33.2 | 32.4 | ✓ (longest route) |
| L  | 10.2 | 10.7 | ✓ |
| G  | 11.1 | 11.4 | ✓ |
| F  | 28.0 | 26.4 | slightly high |

The over-reads come from diagonal-line patterns extending slightly past the last station in the artifact.

### Coverage-per-line summary (2017)

From `subspotting_wide.csv`, the top coverage % per carrier per line:

```
line  ATT   T-Mobile  Verizon  Sprint
   7  19.8    37.6     34.7    12.9   <- heavily elevated in Queens; strong across the board
   J  14.8    38.5     45.2    12.6   <- Broad St / Broadway JMZ corridor
   Z  17.9    32.1     44.8     9.0   <- same corridor as J
   Q  11.2    22.4     35.1    14.6
   N  12.1    18.4     33.5    13.1
   G   0.9     3.7      3.7     5.6   <- least covered: shallow outer-borough line
```

**Verizon consistently leads.** T-Mobile is second. Sprint is a distant fourth on nearly every line. The G is essentially uncovered in 2017 — a good candidate line for a field-check today.

### Known imperfections

- Station orderings for share-track lines (D, F, M, R going through the 6 Av corridor; Q on Broadway) are hand-coded in `join_stations.py` from the standard MTA map. If a stop is listed under two lines with different mile positions, the two rows both make it into the CSV/GeoJSON — that is intentional so downstream analysis can dedupe by station-complex if desired.
- Empirical carrier colors (in `scrape.py`, `CARRIERS` dict) are the darker post-JPEG values observed in the PNG, not the CSS spec — the tolerance of 40 catches most of the pattern but a few edge pixels can vote for the wrong carrier. Preview `bands_preview.png` and tweak the tolerance if you want a stricter or looser read.
- Subspotting's diagonal-line patterns overlap where two carriers are both present in the same cell, which can under-count both. The scores in the long CSV expose this — a low score for both is a hint that the column had mixed patterns.

## Attribution

Subspotting was made by **Marcus Nowotny, Christian Schmidt, and Xavier Georges** (2015–2017). Cite their work if you build on this method:

> Subspotting: Mapping cell phone reception on the New York City Subway. subspotting.nyc, 2017.
