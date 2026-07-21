"""
Chinatown facades — Step 4: build side-by-side comparison strips per lot.

For each BBL with N downloaded facade images, stack them horizontally into a
strip labeled with the year. Writes data/strips/{bbl}.jpg.

Run after fetch_facades.py has produced data/facades/{bbl}/{year_*}.jpg files.
"""

from __future__ import annotations

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
IMG_DIR = DATA / "facades"
OUT_DIR = DATA / "strips"; OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_SIZE = 16
LABEL_HEIGHT = 32


def load_font():
    for candidate in [
        "/System/Library/Fonts/Supplemental/OpenSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]:
        try:
            return ImageFont.truetype(candidate, FONT_SIZE)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def build_strip(bbl_dir: pathlib.Path, font) -> Image.Image | None:
    files = sorted(bbl_dir.glob("*.jpg"))
    if not files:
        return None

    imgs = []
    for f in files:
        target_year = f.name.split("_", 1)[0]
        try:
            im = Image.open(f).convert("RGB")
        except Exception:
            continue
        # Add year label bar under each image
        w, h = im.size
        canvas = Image.new("RGB", (w, h + LABEL_HEIGHT), "black")
        canvas.paste(im, (0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((8, h + 6), target_year, fill="white", font=font)
        imgs.append(canvas)

    if not imgs:
        return None
    total_w = sum(i.width for i in imgs) + (len(imgs) - 1) * 6
    strip = Image.new("RGB", (total_w, imgs[0].height), "black")
    x = 0
    for im in imgs:
        strip.paste(im, (x, 0))
        x += im.width + 6
    return strip


def main() -> int:
    font = load_font()
    lot_dirs = sorted(p for p in IMG_DIR.iterdir() if p.is_dir())
    if not lot_dirs:
        print(f"[!] No lot directories under {IMG_DIR}. Run fetch_facades.py first.")
        return 1

    n_ok = 0
    for d in lot_dirs:
        strip = build_strip(d, font)
        if strip is None:
            continue
        out = OUT_DIR / f"{d.name}.jpg"
        strip.save(out, quality=88)
        n_ok += 1
    print(f"[1] Wrote {n_ok} strips to {OUT_DIR}")

    # Assemble a montage of a sample of strips for at-a-glance inspection.
    sample = sorted(OUT_DIR.glob("*.jpg"))[:12]
    if sample:
        strip_imgs = [Image.open(p) for p in sample]
        w_each = max(s.width for s in strip_imgs)
        h_each = max(s.height for s in strip_imgs)
        cols, rows = 1, len(sample)
        grid = Image.new("RGB", (w_each, h_each * rows + 8 * (rows - 1)), "white")
        y = 0
        for im in strip_imgs:
            grid.paste(im, (0, y))
            y += im.height + 8
        grid.save(DATA / "strips_sample_montage.jpg", quality=85)
        print(f"[2] Wrote montage: {DATA/'strips_sample_montage.jpg'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
