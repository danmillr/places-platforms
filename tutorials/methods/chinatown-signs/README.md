# Chinatown Signs: Facade Extraction, OCR, Color, and Multilingual Embeddings

A full end-to-end analysis pipeline. Companion notebook: `chinatown_signs.ipynb`.

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

## Common pitfalls

- **API cost.** Street View Static is $7 per 1000 requests after $200 monthly credit. Sample sparsely first, then densify.
- **Rate limits.** 500 requests per second is the ceiling but you will hit throttling much sooner. Batch, cache, and retry with backoff.
- **Bad panoramas.** Some sample points return no imagery or return imagery from a different street. Check the returned `pano_id` and log misses.
- **Language mixing.** PaddleOCR needs a language hint. Run it twice (`lang='ch'` and `lang='en'`) and merge results, or use its multilingual model directly.
- **Small text.** Signs at distance are illegible even at 640x640. Request the largest image size and consider re-cropping at higher zoom via the pano.
- **Embedding models drift.** If you rerun a year later, the model may have changed. Pin the version.
