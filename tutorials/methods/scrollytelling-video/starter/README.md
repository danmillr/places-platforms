# Starter — quick start

```bash
cd starter
python3 -m http.server 8000
# open http://localhost:8000
```

Everything you need to edit is in **three places**:

1. **`index.html`** — one `<section class="scene">` per scene. Copy an existing one to add a new scene. Change `data-clip` to point at your video file. Add or remove `<div class="overlay">` blocks inside.
2. **`assets/clips/*.mp4`** — drop your video clips here. See `../README.md` for how to split a long video into clips with `ffmpeg`.
3. **`assets/img/*`** — drop overlay images here.

Optional:
- **`assets/css/style.css`** — change colors, fonts, and layout. Top of file has the palette variables.

That's it. See `../README.md` in the parent folder for the full method (video prep, deployment, extensions).
