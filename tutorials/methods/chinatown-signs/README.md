# Chinatown Signs: Facade Extraction, OCR, Color, and Multilingual Embeddings

A full end-to-end analysis pipeline. Two entry points:

- **`chinatown_signs.ipynb`** — the original notebook. Samples along street centerlines every 80ft, runs the full downstream signs pipeline (OCR + color + embedding + 3D map). Good for the argument about semantic space.
- **`pluto_viewpoints.py` → `discover_panos.py` → `fetch_facades.py` → `build_strips.py` → `write_manifest.py`** — the PLUTO + temporal workflow. One camera per tax lot, aimed at the facade, sampled across every historical Google Street View pass from 2007 to today. Good for change-over-time analysis (turnover, sign replacement, gentrification pace). Documented in the "PLUTO + temporal Street View" section below.
- **`ANALYSIS.md`** — downstream scaffold: how to do sign extraction, color analysis, multilingual OCR, embeddings, 3D reduction, map + 3D visualization, and packaging as a static website. Read this after you've produced the manifest.

Both share the same downstream steps 4-9 (OCR, color, embeddings, maps). Pick your entry based on whether the argument is "what do signs mean in space" (centerline sampling) or "what changed on this lot over N years" (PLUTO temporal).

## What you will build

A structured dataset of signs on Chinatown facades, extracted from Google Street View sampled along street centerlines. For each sign we record:

- Its source image (with `lat`, `lon`, `heading`, `pano_id`, `capture_date`)
- Its bounding box within the image
- The dominant colors of the sign
- The text OCR'd from the sign (Chinese characters, English words, mixed)
- Multilingual embeddings of that text
- A 3D projection of those embeddings via UMAP

The final outputs are:

1. A GeoDataFrame `signs_gdf` (one row per detected sign) with full provenance
2. Choropleth-style maps of color and language distribution
3. A 3D interactive word cloud in embedding space

## Prerequisites

- Python 3.10+
- Google Maps Platform API key with **Street View Static API** enabled
- ~2 GB free disk for image caches (adjustable)
- Ability to run a Jupyter kernel (Colab or local)

## Required packages

```bash
pip install requests pillow numpy pandas geopandas shapely osmnx matplotlib \
            scikit-learn paddleocr paddlepaddle sentence-transformers umap-learn \
            plotly
```

For CPU-only PaddleOCR: `pip install paddlepaddle` (not the GPU variant).

## Design principle: provenance is not optional

The whole point of this pipeline is that every derived value stays linked to the pixel it came from and the location it was seen. If you cannot answer "which corner of which image did this Chinese character come from?" the analysis is not worth publishing.

We enforce this with one master table (`records`) that grows one column at a time:

| Column | Added in step | What it holds |
|---|---|---|
| `sample_id` | 2 | UUID for a sample point on a street |
| `lat`, `lon` | 2 | Coordinates of the sample point |
| `heading` | 2 | Compass heading of the Street View camera |
| `pano_id` | 3 | Google's Street View pano identifier |
| `capture_date` | 3 | When the panorama was taken |
| `image_path` | 3 | Local path to the downloaded JPEG |
| `sign_id` | 4 | UUID per detected sign |
| `bbox` | 4 | `[x, y, w, h]` in image pixels |
| `sign_crop_path` | 4 | Local path to the cropped sign JPEG |
| `colors` | 5 | List of `(r, g, b, weight)` tuples |
| `dominant_color_hex` | 5 | Top color as hex |
| `ocr_text` | 6 | Full OCR string |
| `ocr_language` | 6 | Detected language(s) |
| `chinese_chars` | 6 | Only the CJK characters |
| `english_words` | 6 | Only the ASCII/Latin words |
| `embedding` | 7 | 384-dim or 1024-dim vector |
| `x3d`, `y3d`, `z3d` | 8 | UMAP coordinates |

Every step reads from and writes to this table. Never derive off a subset without a merge back.

## Pipeline steps

1. **Study area.** Pull the Chinatown boundary and street centerlines from OSM via osmnx.
2. **Sample points.** Walk each centerline at a fixed interval (e.g., 20 m). At each point, generate two viewpoints, one facing each side of the street, offset by 90 degrees from the street's local bearing.
3. **Pull Street View images.** Call the Street View Static API with the point coordinate and heading. Save image + metadata.
4. **Detect signs.** Two options in the notebook:
   - **Cheap:** rely on OCR to find text regions; treat each text region as a "sign candidate"
   - **Better:** run a foundation model (Google Vision `objectLocalization`, or a YOLO fine-tuned on signs) to find bounding boxes first, OCR inside them
5. **Extract dominant colors.** Reshape each sign crop's pixels, k-means to `k=3` clusters, record the cluster centers weighted by size.
6. **OCR.** Run PaddleOCR (multilingual) on each sign crop. Split output into Chinese and English tokens.
7. **Embed.** Use `paraphrase-multilingual-MiniLM-L12-v2` from sentence-transformers to embed every OCR token. Chinese and English land in the same space.
8. **Reduce to 3D.** UMAP with `n_components=3`.
9. **Visualize.** Choropleth of dominant colors and language mix. 3D scatter of embeddings with text labels.

## Interpreting the 3D word cloud

Embeddings position tokens by learned semantic similarity. In a multilingual model:

- Chinese and English translations of the same concept sit near each other
- Semantically related but linguistically unrelated words (e.g., "restaurant" and "食") cluster
- Character-level Chinese tokens can behave differently from word-level English tokens; expect Chinese to sometimes form its own dense region if you tokenize by character
- UMAP is nonlinear; distances after reduction are qualitative, not metric. Do not calculate cosine similarity on `x3d, y3d, z3d`. Do it on the original embedding.

The notebook walks through:
- What the raw 384-dim vector looks like
- Why UMAP is used instead of PCA
- What "closer" means and does not mean after reduction
- How to sanity-check by finding nearest neighbors in the full-dim space

## Extensions

- Fine-tune a YOLO on signs from your own labeled images
- Compare Manhattan Chinatown, Flushing, and Sunset Park with the same pipeline
- Longitudinal: pull historical panos from `capture_date` filters, compare 2011 vs today
- Sound: pair signs with audio scraped from adjacent shopfronts

## Ethical and legal considerations

- Google Street View images are Google's copyright. Fair use for research generally applies to derived data, not to redistributing the raw JPEGs. Do not publish the image cache.
- Small business signage is public but people are not. Blur or crop out faces if they appear in your outputs.
- Attribution: cite Google Street View, OSM, and any labeled datasets you used to train detectors.
- If you publish an interactive map of businesses' signage, contact the businesses for public-facing deliverables. Academic papers are different from public tools.

## PLUTO + temporal Street View

An alternate entry into the pipeline: sample **one camera per tax lot, facing the facade**, across every year of Google Street View coverage from 2007 onward. Use this when the question is *what changed at this address over time* (sign turnover, storefront replacement, physical renovation).

### The four scripts

```bash
python3 pluto_viewpoints.py    # NYC PLUTO -> data/pluto_viewpoints.csv (1 row per lot)
python3 discover_panos.py      # streetlevel -> data/pano_index.csv    (~11 panos per lot)
export GOOGLE_MAPS_API_KEY=...
python3 fetch_facades.py       # -> data/facades/{bbl}/{year_*}.jpg
python3 build_strips.py        # -> data/strips/{bbl}.jpg  (side-by-side year comparison)
```

### Step-by-step

1. **PLUTO lots.** Query NYC Open Data resource `64uk-42ks` (MapPLUTO) with a lat/lon bbox filter. Chinatown study area (Grand-Worth-Bowery-Broadway) returns ~1,026 tax lots with centroid coordinates, address, building class, year built, unit counts, and assessed value. No shapefile download needed — the SODA API returns everything.

2. **Compute facade-facing camera per lot.** For each lot:
   - Load OSM walk-network edges via `osmnx.graph_from_bbox(...)`.
   - Reproject to EPSG:2263 (NY State Plane, feet) so distances are meaningful.
   - For each lot centroid, find the nearest street edge with the spatial index.
   - Camera position = the closest point on that edge; camera heading = bearing from that camera position to the lot centroid.
   - This gives one row per lot with `(bbl, address, cam_lat, cam_lon, heading_deg, cam_to_lot_ft)`.

3. **Enumerate historical panoramas with `streetlevel`.** The Google Street View Static API does not surface Time Machine panos, but the community-maintained [`streetlevel`](https://github.com/sk-zk/streetlevel) library scrapes Google's internal API to return them. For each camera position:
   - `streetview.find_panorama(cam_lat, cam_lon, radius=25)` gets the most recent pano.
   - Its `.historical` list contains every past capture at that location (typically 8-14 in Manhattan, from 2007 through today).
   - For each pano, recompute the heading from the pano's *actual* car position to the lot centroid, because the pano may sit 5-15 m away from where you asked.

4. **Pick one pano per target year.** For each lot, choose the pano nearest to each target year (default: 2007, 2011, 2014, 2018, 2022, current). Ties broken by month. Some lots have no 2007 pano — the picker will fall back to the closest available and record `actual_year`.

5. **Fetch via Street View Static API by `pano_id`.** The Static API's `pano` parameter lets you request a specific captured pano, including historical ones once you know the ID. Cost is $7/1000 requests after the $200 monthly free credit (~28.5k free images/month).

6. **Build comparison strips.** `build_strips.py` composes each lot's yearly images horizontally with year labels, producing a single JPEG that tells the change story at a glance.

### Notes and gotchas

- **`streetlevel` is unofficial.** It works reliably as of this method's authoring but relies on Google's internal API which can change. For academic research this is fine; for a public deployment or client work, wrap `find_panorama` calls in try/except and cache the results.
- **Historical panos require macOS deps.** `streetlevel` pulls in `pyexiv2` which pulls in `brotli` and `inih` native libs. On macOS, `brew install brotli inih` may not be sufficient — the Homebrew brotli formula (as of Oct 2025) creates a self-referencing symlink at `/opt/homebrew/Cellar/brotli/<v>/lib/libbrotlidec.1.dylib` that must be repointed at `libbrotlidec.1.2.0.dylib` before `pyexiv2` will import.
- **PLUTO lat/lon are lot centroids.** Interior lots on large parcels may sit 100+ ft from the nearest street; the camera-to-lot distance shows this. For frontage-oriented analysis, filter to `cam_to_lot_ft < 80` or compute a proper front-facade midpoint by intersecting the lot polygon with the street buffer.
- **Same pano, different lots.** A single Google car photo often serves 3-5 adjacent lots at different headings — each is a separate Static API request and separate billing. If your budget is tight, deduplicate by `pano_id` first and just crop the same pano at multiple headings client-side.
- **Coverage is not uniform in time.** 2007 was Google's first NYC pass; some streets were skipped. 2010 and 2015 have thin coverage. The picker's `actual_year` column lets you audit which target years actually got matched.
- **Google's ToS.** Fair-use quotation of derived analytics is fine for research; do not redistribute raw image caches. Cite Google Street View + capture date in any deliverable.

### What good outputs look like

- `data/pluto_viewpoints.csv`: ~1,026 rows for Chinatown, each with a camera position and heading.
- `data/pano_index.csv`: ~11,000 rows (11 panos × 1,026 lots), spanning 2007-2026.
- `data/fetch_plan.csv`: ~6,156 rows (6 target years × 1,026 lots).
- `data/facades/<bbl>/2007_*.jpg`, `.../2011_*.jpg`, ...: one JPEG per (lot, target-year).
- `data/strips/<bbl>.jpg`: a single horizontal strip that shows the same address across all six years.

Feeding these into the downstream OCR / color / embedding steps of `chinatown_signs.ipynb` lets you compute things like:

- Fraction of signs that changed script (Chinese-only → English-only) per lot per decade.
- Turnover velocity: how often does the dominant sign color at a lot change?
- Color-shift clustering: do gentrifying corridors show a common color drift?

## Common pitfalls

- **API cost.** Street View Static is $7 per 1000 requests after $200 monthly credit. Sample sparsely first, then densify.
- **Rate limits.** 500 requests per second is the ceiling but you will hit throttling much sooner. Batch, cache, and retry with backoff.
- **Bad panoramas.** Some sample points return no imagery or return imagery from a different street. Check the returned `pano_id` and log misses.
- **Language mixing.** PaddleOCR needs a language hint. Run it twice (`lang='ch'` and `lang='en'`) and merge results, or use its multilingual model directly.
- **Small text.** Signs at distance are illegible even at 640x640. Request the largest image size and consider re-cropping at higher zoom via the pano.
- **Embedding models drift.** If you rerun a year later, the model may have changed. Pin the version.
