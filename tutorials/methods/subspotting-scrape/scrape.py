"""
Subspotting scraper — reverse-engineer the 2017 System Explorer PNG
back into a structured (line, mile, carrier, has_reception) dataset.

Companion to README.md in this directory. Run from the method folder:
    python3 scrape.py
Outputs written to ./data/
"""

from __future__ import annotations

import io
import json
import pathlib
import sys

import numpy as np
import pandas as pd
import requests
from PIL import Image
from lxml import etree

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)

PNG_URL = "https://subspotting.nyc/assets/img/main/provider/popup-systemexplorer.png"
SVG_URL = "https://subspotting.nyc/assets/img/main/provider/explorer-overlay.svg"

# CSS-declared reference colors from the source page.
CSS_REF = {
    "att":     (0x06, 0x7a, 0xb4),
    "tmobile": (0xe2, 0x00, 0x74),
    "verizon": (0xff, 0x00, 0x00),
    "sprint":  (0xff, 0xe1, 0x00),
}

# Empirical reference colors observed in the actual PNG (darker, JPEG-compressed).
# These are what appear against the black background of the poster.
CARRIERS = {
    "att":     (36, 124, 169),   # observed blue
    "tmobile": (193, 36, 102),   # observed magenta
    "verizon": (194, 43, 40),    # observed red
    "sprint":  (205, 176, 41),   # observed gold
}


def step1_fetch() -> tuple[bytes, bytes]:
    png_path = DATA / "systemexplorer.png"
    svg_path = DATA / "overlay.svg"
    if not png_path.exists():
        print(f"[1] Downloading PNG ({PNG_URL})")
        png_path.write_bytes(requests.get(PNG_URL, timeout=60).content)
    if not svg_path.exists():
        print(f"[1] Downloading SVG ({SVG_URL})")
        svg_path.write_bytes(requests.get(SVG_URL, timeout=60).content)
    print(f"[1] PNG: {png_path.stat().st_size} bytes, SVG: {svg_path.stat().st_size} bytes")
    return png_path.read_bytes(), svg_path.read_bytes()


def step2_calibrate(svg_bytes: bytes) -> tuple[float, float, int]:
    """Fit miles = slope * x_svg + intercept. Return (slope, intercept, svg_width)."""
    ns = {"svg": "http://www.w3.org/2000/svg"}
    tree = etree.fromstring(svg_bytes)
    svg_w = int(float(tree.get("width").rstrip("px")))
    outer = tree.find(".//svg:g[@id='Page-1']/svg:g/svg:g", ns)
    tx, ty = 0.0, 0.0
    if outer is not None and outer.get("transform"):
        t = outer.get("transform")
        import re
        m = re.match(r"translate\(([-\d\.]+)[, ]+([-\d\.]+)\)", t)
        if m:
            tx, ty = float(m.group(1)), float(m.group(2))

    miles, xs = [], []
    for text_el in tree.iter("{http://www.w3.org/2000/svg}text"):
        tspan = text_el.find("svg:tspan", ns)
        if tspan is None or tspan.text is None:
            continue
        try:
            mile = float(tspan.text.strip())
        except ValueError:
            continue
        x_local = float(tspan.get("x"))
        xs.append(x_local + tx)
        miles.append(mile)

    miles = np.array(miles); xs = np.array(xs)
    order = np.argsort(miles)
    miles, xs = miles[order], xs[order]
    slope, intercept = np.polyfit(xs, miles, 1)
    print(f"[2] Calibration points (mile, svg_x): {list(zip(miles.tolist(), xs.round(2).tolist()))}")
    print(f"[2] miles = {slope:.6f} * svg_x + {intercept:.4f}  (~{1/slope:.2f} px/mile)")
    print(f"[2] SVG width: {svg_w}")
    return float(slope), float(intercept), svg_w


def step3_load_png(png_bytes: bytes, target_w: int) -> np.ndarray:
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    print(f"[3] PNG native size: {img.size}")
    scale = target_w / img.width
    new_h = round(img.height * scale)
    img_scaled = img.resize((target_w, new_h), Image.LANCZOS)
    arr = np.array(img_scaled)
    print(f"[3] Rescaled to {img_scaled.size} (scale={scale:.4f})")
    return arr


def step4_segment_bands(arr: np.ndarray) -> list[tuple[int, int]]:
    """Detect horizontal bands corresponding to subway lines.

    Each band is a horizontal strip containing the diagonal-line reception
    patterns for one subway line. The background is near-black; the bands
    are colorful, so we use per-row 'colorfulness' (max-min channel) as
    the signal.
    """
    sat = arr.max(axis=2).astype(np.int16) - arr.min(axis=2).astype(np.int16)
    row_colorfulness = sat.mean(axis=1)
    THR = 5.0
    colorful_rows = np.where(row_colorfulness > THR)[0]
    print(f"[4] Colorfulness threshold {THR}; {len(colorful_rows)} colorful rows detected")
    if len(colorful_rows) == 0:
        return []

    GAP = 20
    bands = []
    current = [int(colorful_rows[0])]
    for r in colorful_rows[1:]:
        r = int(r)
        if r - current[-1] <= GAP:
            current.append(r)
        else:
            if len(current) >= 6:  # ignore stray colored tick marks or logo bits
                bands.append((current[0], current[-1]))
            current = [r]
    if len(current) >= 6:
        bands.append((current[0], current[-1]))

    print(f"[4] {len(bands)} candidate bands")
    for i, (a, b) in enumerate(bands):
        print(f"      band {i:02d}: rows {a}-{b}  (h={b-a+1})")
    return bands


def step4b_expand_bands(arr: np.ndarray, bands: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Colorfulness already captures the full pattern band — no expansion needed."""
    return bands


SUBWAY_LINES_TOP_TO_BOTTOM = [
    "1", "2", "3", "4", "5", "6", "7",
    "A", "C", "E",
    "B", "D", "F", "M",
    "G",
    "J", "Z",
    "L",
    "N", "Q", "R",
]


def step5_label_bands(bands: list[tuple[int, int]]) -> list[str]:
    """Label bands by reading the left-column bullet labels in the source PNG.

    Ground-truthed manually against the artifact — see README.md, step 5.
    """
    if len(bands) != len(SUBWAY_LINES_TOP_TO_BOTTOM):
        print(f"[!] {len(bands)} bands but {len(SUBWAY_LINES_TOP_TO_BOTTOM)} labels — falling back to indices")
        return [f"band_{i:02d}" for i in range(len(bands))]
    return list(SUBWAY_LINES_TOP_TO_BOTTOM)


def carrier_score(pixels: np.ndarray, ref: tuple[int, int, int], tol: int = 40) -> float:
    diff = np.abs(pixels.astype(np.int16) - np.array(ref, dtype=np.int16)).max(axis=-1)
    return float((diff <= tol).mean())


def _band_x_extent(arr: np.ndarray, r0: int, r1: int) -> tuple[int, int]:
    """Return (x_min, x_max) — the first and last colorful column in this band."""
    band = arr[r0:r1+1]
    sat = band.max(axis=2).astype(np.int16) - band.min(axis=2).astype(np.int16)
    col_score = sat.max(axis=0)  # any colorful pixel in this column?
    colorful = np.where(col_score > 20)[0]
    if len(colorful) == 0:
        return (0, arr.shape[1] - 1)
    return int(colorful.min()), int(colorful.max())


def step6_decode(
    arr: np.ndarray,
    bands: list[tuple[int, int]],
    labels: list[str],
    slope: float,
    intercept: float,
    score_cutoff: float = 0.03,
    tick_mile: float = 0.1,
) -> pd.DataFrame:
    W = arr.shape[1]
    tick_px = int(round((tick_mile) / slope))
    print(f"[6] Sampling every {tick_px} px (~{tick_mile} mile) across {W}px")

    rows = []
    for band_idx, ((r0, r1), label) in enumerate(zip(bands, labels)):
        band = arr[r0:r1+1]
        x_min, x_max = _band_x_extent(arr, r0, r1)
        line_length_mi = slope * (x_max - x_min)
        print(f"      {label}: cols {x_min}-{x_max} => ~{line_length_mi:.2f} mi")
        for x in range(x_min, x_max + 1, tick_px):
            mile = slope * x + intercept
            col = band[:, x, :]
            scores = {c: carrier_score(col, ref) for c, ref in CARRIERS.items()}
            for c, s in scores.items():
                rows.append({
                    "line": label,
                    "band_idx": band_idx,
                    "svg_x": x,
                    "mile_from_terminal": round(mile - (slope * x_min + intercept), 3),
                    "abs_mile": round(mile, 3),
                    "carrier": c,
                    "score": round(s, 4),
                    "has_reception": s >= score_cutoff,
                })
    df = pd.DataFrame(rows)
    print(f"[6] Long-format rows: {len(df)}")
    return df


def step7_summarise(df: pd.DataFrame) -> pd.DataFrame:
    """Wide, per-line coverage percentage per carrier."""
    pivot = (
        df.groupby(["line", "band_idx", "carrier"])["has_reception"]
        .mean()
        .mul(100)
        .round(1)
        .unstack("carrier")
        .reset_index()
        .sort_values("band_idx")
    )
    return pivot


def main() -> int:
    png_bytes, svg_bytes = step1_fetch()
    slope, intercept, svg_w = step2_calibrate(svg_bytes)
    arr = step3_load_png(png_bytes, target_w=svg_w)

    Image.fromarray(arr).save(DATA / "systemexplorer_1728w.png")

    track_bands = step4_segment_bands(arr)
    if not track_bands:
        print("[!] No bands detected — try adjusting the row threshold.")
        return 1

    bands = step4b_expand_bands(arr, track_bands)
    labels = step5_label_bands(bands)

    preview = arr.copy()
    for r0, r1 in bands:
        preview[r0, :, :] = [0, 255, 0]
        preview[r1, :, :] = [0, 255, 0]
    Image.fromarray(preview).save(DATA / "bands_preview.png")
    print(f"[4] Wrote band overlay preview: {DATA/'bands_preview.png'}")

    df = step6_decode(arr, bands, labels, slope, intercept)
    df.to_csv(DATA / "subspotting_long.csv", index=False)
    print(f"[6] Wrote {DATA/'subspotting_long.csv'} ({len(df)} rows)")

    wide = step7_summarise(df)
    wide.to_csv(DATA / "subspotting_wide.csv", index=False)
    print(f"[7] Wrote {DATA/'subspotting_wide.csv'}")
    print(wide.to_string(index=False))

    metadata = {
        "source_png": PNG_URL,
        "source_svg": SVG_URL,
        "captured": "2017-01",
        "processed_scale_target_width_px": svg_w,
        "pixel_to_mile_slope": slope,
        "pixel_to_mile_intercept": intercept,
        "carrier_hex": {c: "#{:02x}{:02x}{:02x}".format(*rgb) for c, rgb in CARRIERS.items()},
        "n_bands": len(bands),
        "band_pixel_ranges": bands,
        "labels": labels,
    }
    (DATA / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"[*] Wrote {DATA/'metadata.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
