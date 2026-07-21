# Chinatown Facades — Analysis and Web Scaffolding Guide

You now have **6,030 date-stamped facade images** covering 1,005 Chinatown tax lots across six target years (2007-2026), plus a manifest that joins every image back to its lot, address, PLUTO attributes, and pano metadata.

This document is the **downstream half** of the method: how to turn those images into structured data, how to visualize the result on a map and in embedding space, and how to package it as a website. The upstream half (image collection) is documented in `README.md` under "PLUTO + temporal Street View."

Nothing in this document has to be executed in order — pick the sections that match the argument your project is making, and skip the rest.

---

## 1. What you're starting with

### Files (all in `data/`)

| File | Role |
|---|---|
| `pluto_viewpoints.csv` | Lot list with one facade-facing camera per BBL. Upstream of everything. |
| `pano_index.csv` | Every historical Google Street View pano `streetlevel` found per lot. |
| `fetch_plan.csv` | Chosen pano per (BBL, target year). |
| `facades/{bbl}/{target_year}_{actual_year}_{pano_date}.jpg` | The images themselves. |
| `strips/{bbl}.jpg` | 6-panel year comparison strip per lot. |
| `facades_manifest.csv` | **The primary table for downstream work.** One row per image. |
| `facades_manifest.geojson` | Same, geometry = pano capture location. Ready for MapLibre / QGIS. |
| `strips_manifest.csv` | One row per lot with strip path + year span. |

### The manifest schema

`facades_manifest.csv` is the join table. Every downstream operation should read it, do work keyed by `image_path`, and merge results back.

| Column | Type | What it holds |
|---|---|---|
| `image_path` | str | Relative path — **the primary key** |
| `strip_path` | str | Path to the lot's year-comparison strip (repeats across the 6 rows for one BBL) |
| `bbl` | str | Borough-block-lot identifier — join key to PLUTO and to sibling years |
| `address` | str | From PLUTO |
| `target_year` | int | The year the pipeline asked for (2007, 2011, 2014, 2018, 2022, 2026) |
| `actual_year` | int | The year of the pano actually returned |
| `year_delta` | int | `actual_year - target_year` |
| `pano_date` | str | `YYYY-MM` |
| `pano_id` | str | Google's pano identifier |
| `pano_lat`, `pano_lon` | float | Where Google's car was |
| `lot_lat`, `lot_lon` | float | PLUTO lot centroid |
| `heading_deg` | float | Camera direction (degrees clockwise from north) |
| `cam_to_lot_ft` | float | Distance from pano to lot centroid |
| `bldgclass`, `landuse` | str/float | PLUTO building class + land-use code |
| `yearbuilt`, `numbldgs` | int | PLUTO |
| `unitstotal`, `unitsres` | int | PLUTO unit counts |

### Design principle: the manifest is the spine

Any per-image output you compute (a sign bounding box, an OCR string, a color palette, an embedding) must be joinable back to `image_path`. Save your derived tables with `image_path` as a column and left-merge back onto the manifest. Never fan out to a subset without merging back.

---

## 2. Sign extraction

Two paths, cheap and better.

### Cheap: OCR-as-detector

PaddleOCR's detection stage returns text-region rectangles for free. Treat every text region as a sign candidate. This works well for storefront signage because Chinatown signs are mostly text; it misses pictorial signs (dragons, produce, symbols) and mistakes storefront reflections for text.

```python
import pandas as pd
from paddleocr import PaddleOCR
from PIL import Image

ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
manifest = pd.read_csv('data/facades_manifest.csv')

sign_rows = []
for _, r in manifest.iterrows():
    result = ocr.ocr(r.image_path)
    if not result or not result[0]:
        continue
    for det in result[0]:
        (x1,y1),(x2,y2),(x3,y3),(x4,y4) = det[0]
        text, conf = det[1]
        sign_rows.append({
            'image_path': r.image_path,           # <- join key
            'sign_id': f"{r.bbl}_{r.target_year}_{len(sign_rows)}",
            'bbox': [int(min(x1,x4)), int(min(y1,y2)),
                     int(max(x2,x3)-min(x1,x4)), int(max(y3,y4)-min(y1,y2))],
            'ocr_text': text,
            'ocr_confidence': conf,
        })

signs = pd.DataFrame(sign_rows)
signs.to_csv('data/signs.csv', index=False)
```

### Better: a real detector

Fine-tune a YOLO on a labeled sample of signs from your own images, or use Google Vision's `objectLocalization`. Use OCR only inside the returned bounding boxes. This catches non-textual storefront signage that OCR would ignore, and improves crop quality.

```python
# Rough scaffolding — labels must come from you, not from OCR.
from ultralytics import YOLO
model = YOLO('yolov8n.pt')  # start with COCO weights
# label ~200 signs across ~20 images to fine-tune, then:
model.train(data='signs.yaml', epochs=40, imgsz=640)
```

### Cropping and saving

For every sign detected, save a crop keyed by `sign_id` and record it in the signs table.

```python
for _, r in signs.iterrows():
    img = Image.open(r.image_path)
    x, y, w, h = r.bbox
    img.crop((x, y, x + w, y + h)).save(f'data/crops/{r.sign_id}.jpg')
```

---

## 3. Color analysis

K-means the pixels of each sign crop; cluster centers are the palette, cluster sizes are weights.

```python
from sklearn.cluster import KMeans
import numpy as np

def dominant_colors(image_path, k=3):
    img = Image.open(image_path).convert('RGB').resize((80, 80))
    px = np.array(img).reshape(-1, 3)
    km = KMeans(n_clusters=k, n_init=4, random_state=0).fit(px)
    counts = np.bincount(km.labels_, minlength=k)
    order = counts.argsort()[::-1]
    return [(tuple(int(x) for x in km.cluster_centers_[i]),
             int(counts[i])) for i in order]

signs['colors'] = signs['sign_id'].map(
    lambda sid: dominant_colors(f'data/crops/{sid}.jpg')
)
signs['dominant_hex'] = signs['colors'].map(
    lambda cs: '#{:02x}{:02x}{:02x}'.format(*cs[0][0])
)
```

Useful derived questions:
- What are the ten most-common dominant colors across all signs, all years?
- Does the color palette of signs on a given block shift toward cooler / warmer hues over time?
- Which lots' signs kept the same dominant color across all six years (stable identity) vs which flipped repeatedly (churn)?

---

## 4. Multilingual OCR — Chinese and English separately

Signs mix scripts. Split the raw OCR string into CJK and Latin components using Unicode ranges.

```python
import re
CJK = re.compile(r'[一-鿿㐀-䶿]+')          # Unified Ideographs + Extension A
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'&\-]*")

def split_text(t):
    if not isinstance(t, str):
        return [], []
    return CJK.findall(t), LATIN_WORD.findall(t)

signs[['chinese_chars', 'english_words']] = signs['ocr_text'].apply(
    lambda t: pd.Series(split_text(t))
)
signs['lang'] = signs.apply(
    lambda r: ('mixed' if r.chinese_chars and r.english_words
               else 'chinese' if r.chinese_chars
               else 'english' if r.english_words
               else 'other'), axis=1
)
```

For a temporal argument, aggregate per lot per year:

```python
merged = manifest.merge(signs, on='image_path')
mix = (merged
       .groupby(['bbl', 'actual_year'])['lang']
       .value_counts(normalize=True)
       .unstack(fill_value=0))
# now `mix` has one row per (lot, year) with fractions for chinese/english/mixed
```

---

## 5. Multilingual embeddings

`paraphrase-multilingual-MiniLM-L12-v2` from sentence-transformers puts 50+ languages into a shared 384-dim space. Chinese and English translations of the same concept end up as neighbors — which is what lets the 3D cloud tell a semantic story instead of a language-clustering story.

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

# One token per row (character-level for CJK, word-level for Latin)
tokens = []
for _, r in signs.iterrows():
    for z in r.chinese_chars or []:
        for ch in z:  # character-level
            tokens.append({'sign_id': r.sign_id, 'token': ch, 'lang': 'zh'})
    for w in r.english_words or []:
        tokens.append({'sign_id': r.sign_id, 'token': w, 'lang': 'en'})
tokens_df = pd.DataFrame(tokens)

tokens_df['embedding'] = list(model.encode(tokens_df['token'].tolist(), batch_size=64))
```

The `embedding` column is a 384-dim numpy vector. Do all similarity math on this (cosine) before any dimension reduction.

---

## 6. Dimension reduction — the 3D cloud

UMAP preserves local neighborhoods better than PCA and produces layouts that read like word clouds. Reduce to 3D for a scatter plot, but keep the full-dim vector for any actual similarity query.

```python
import umap
import numpy as np

X = np.stack(tokens_df['embedding'].values)
reducer = umap.UMAP(n_components=3, n_neighbors=15, min_dist=0.1,
                    metric='cosine', random_state=0)
coords = reducer.fit_transform(X)
tokens_df[['x3d', 'y3d', 'z3d']] = coords
```

Interpretation:
- Chinese and English translations sit near each other (e.g., 麵 near "noodle")
- Semantically related but linguistically unrelated tokens cluster
- UMAP is nonlinear — treat distances after reduction as qualitative

---

## 7. Visualization

### 7a. Map: signs in space

The manifest is already spatial. Load the GeoJSON directly into MapLibre, style by any derived attribute.

```python
import geopandas as gpd
from shapely.geometry import Point

# Signs table -> per-lot summary -> GeoJSON
per_lot = (
    signs.merge(manifest[['image_path','lot_lat','lot_lon','bbl','address']],
                on='image_path')
    .groupby(['bbl','address','lot_lat','lot_lon'])
    .agg(n_signs=('sign_id','count'),
         chinese_frac=('lang', lambda s: (s=='chinese').mean()),
         english_frac=('lang', lambda s: (s=='english').mean()),
         mixed_frac=('lang', lambda s: (s=='mixed').mean()),
         dominant_color=('dominant_hex', lambda s: s.mode().iloc[0] if len(s.mode()) else '#888'))
    .reset_index()
)
gdf = gpd.GeoDataFrame(
    per_lot, geometry=gpd.points_from_xy(per_lot.lot_lon, per_lot.lot_lat), crs=4326
)
gdf.to_file('data/signs_per_lot.geojson', driver='GeoJSON')
```

Maps worth building:
- **Choropleth of dominant color per lot** — a color-swatch dot at each address
- **Language mix as pie or bar per lot** — small multiples
- **Change ribbon** — for a chosen lot, animate through target years
- **Change intensity** — one dot per lot, size = number of sign changes across years

### 7b. 3D embedding cloud

Plotly Express is the fastest path to an interactive 3D scatter. Save as standalone HTML for embedding into a static site.

```python
import plotly.express as px

fig = px.scatter_3d(
    tokens_df, x='x3d', y='y3d', z='z3d',
    color='lang', hover_data=['token'],
    title='Chinatown signs — multilingual embedding (2007-2026)'
)
fig.update_traces(marker=dict(size=3, opacity=0.75))
fig.write_html('site/embedding_cloud.html', include_plotlyjs='cdn')
```

For a more polished cloud: three.js with `THREE.Points`, custom shaders for glow, and click-to-reveal for the source sign crop. That is a real project on its own — build the Plotly version first, decide if you need custom.

---

## 8. Building the website

Follow the pattern in `tutorials/methods/realtime-subway-positions/` — no build system, just static HTML served with `python3 -m http.server 8000` and deployed to GitHub Pages.

### Minimum viable structure

```
site/
├── index.html                  # landing page + argument
├── map.html                    # MapLibre map of signs per lot
├── explore.html                # click a lot → see its strip + signs
├── embedding.html              # Plotly 3D cloud (iframe or inline)
├── about.html                  # method + attribution + limitations
├── assets/
│   ├── css/                    # one stylesheet, no framework needed
│   ├── js/                     # small handlers per page
│   └── data/
│       ├── signs_per_lot.geojson
│       ├── strips/{bbl}.jpg   # copied or symlinked from ../data/strips
│       └── crops/*.jpg        # if you want to show individual signs
```

### Map page — MapLibre skeleton

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Chinatown facades — where signs change</title>
  <link href="https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.css" rel="stylesheet" />
  <link href="assets/css/site.css" rel="stylesheet" />
</head>
<body>
  <header><h1>Chinatown facades</h1><p>1,005 tax lots, 6 years, 6,030 photos.</p></header>
  <div id="map"></div>
  <aside id="detail">
    <img id="strip" src="" alt="" />
    <p id="address"></p>
    <ul id="signs"></ul>
  </aside>
  <script src="https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.js"></script>
  <script>
    const map = new maplibregl.Map({
      container: 'map',
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [-73.9975, 40.7165],
      zoom: 15,
    });
    map.on('load', async () => {
      const data = await fetch('assets/data/signs_per_lot.geojson').then(r=>r.json());
      map.addSource('lots', {type: 'geojson', data});
      map.addLayer({
        id: 'lots', type: 'circle', source: 'lots',
        paint: {
          'circle-radius': ['interpolate',['linear'],['get','n_signs'], 0,3, 20,10],
          'circle-color': ['get','dominant_color'],
          'circle-stroke-width': 1, 'circle-stroke-color': '#111',
        }
      });
      map.on('click', 'lots', e => {
        const p = e.features[0].properties;
        document.getElementById('address').textContent = p.address;
        document.getElementById('strip').src = 'assets/data/strips/' + p.bbl + '.jpg';
      });
    });
  </script>
</body>
</html>
```

### Style principles for "simple and beautiful"

- **One typeface, two weights.** Regular for body, bold for titles. Serif like *EB Garamond* or geometric sans like *Inter*, *IBM Plex Sans*, or *Open Sans*. Load from Google Fonts.
- **A restrained palette.** 3-5 colors max. Neutral background (`#f6f4ee` or `#111`), one accent, one signal color. Consider matching the dominant-color logic from your dataset — let the signs tell you the palette.
- **Whitespace over decoration.** Generous margins, small type sizes for body (~15px), large type only for titles.
- **One map, one action.** Do not build a control panel. The map should teach itself: hover for name, click for the strip, that's it.
- **Small text.** Tight hierarchy: `h1` for the site name, `h2` for section, no `h3` unless necessary.
- **No animation for its own sake.** The temporal story lives in the strips; do not autoplay year sliders. Let the user drive.
- **Cite everything on `about.html`.** Google Street View, MTA / PLUTO, streetlevel, Cornell ARCH 6133, your name and date.

### Deploying

```bash
git init && git add . && git commit -m "chinatown facades site"
git remote add origin git@github.com:<you>/<repo>.git
git push -u origin main
# In repo settings → Pages → Deploy from branch → main / (root)
```

GitHub Pages will serve the site at `https://<you>.github.io/<repo>/`. The `.geojson` and images are static; no server needed.

---

## 9. Bringing your own analysis

Anything you can compute per image can plug in. The recipe:

1. **Read the manifest.** `pd.read_csv('data/facades_manifest.csv')`
2. **Compute one derived table.** One row per `image_path` (or per `sign_id`), with your new columns.
3. **Merge back.** `merged = manifest.merge(your_table, on='image_path')`
4. **Persist alongside the manifest.** Write to `data/derived/<yourname>.csv`. Do not overwrite `facades_manifest.csv`.

Examples of analyses that would extend this pipeline:

- **Facade change score** — compute perceptual hash of each year's image; per lot, sum the pairwise hash distances across consecutive years. High score = high physical churn.
- **Sign-turnover rate** — for each lot, how many distinct dominant colors did its signs have across 6 years?
- **Language drift** — per lot, plot `chinese_frac` vs year. Fit a linear trend. Which lots trended toward English fastest?
- **Cross-borough comparison** — rerun the full pipeline with a different bbox (East Harlem, Flushing, Sunset Park). Compare the same metric across three Chinatowns.
- **Cross-reference PLUTO change** — join to `yearalter1` and `yearalter2` from PLUTO. Do sign-color shifts coincide with recorded alterations?
- **Business Improvement District overlay** — pull the Chinatown BID boundary and compare on-BID vs off-BID sign metrics.
- **Rent-stabilized building overlay** — from NYC's Rent Stabilized Housing dataset, tag lots. Do RS lots show different turnover patterns?
- **Historic district overlay** — PLUTO's `histdist` column already has this. Lots in a historic district vs not.
- **Contribute back to the method.** If you find a robust sign detector or an OCR post-processing rule that improves quality, submit it back as a PR to `chinatown_signs.ipynb`.

Whatever you add, the invariant is the same: `image_path` is the primary key. Keep it in every derived table. Never publish an analysis whose rows cannot be re-linked to a specific image.

---

## Attribution and limitations

Cite in every deliverable:

- **Subspotting method inspiration:** Cornell ARCH 6133 Places / Platforms, chinatown-signs method.
- **Imagery:** Google Street View captures, dates as noted per image. `pano_id` values are Google's.
- **Historical Street View access:** `streetlevel` Python library (unofficial; scrapes Google's internal API).
- **Lot data:** NYC Department of City Planning, MapPLUTO. NYC Open Data resource `64uk-42ks`.
- **Streets:** OpenStreetMap contributors via osmnx.

Limitations to disclose:

- Sample is Google's coverage, not ours. Streets Google skipped are absent regardless of what happened there.
- OCR quality on small storefront signage is imperfect; expect ~5-15% character-level error, more on angled or reflective signs.
- The "year" of a photo is a capture date; the sign may predate it by years and outlast it by more.
- `streetlevel` is unofficial and can break if Google changes its internal API. Cache aggressively; do not depend on live discovery for a published site.
- The image cache (342 MB) is Google's copyright. Do not redistribute the JPEGs; publish derived analytics and thumbnails only.
