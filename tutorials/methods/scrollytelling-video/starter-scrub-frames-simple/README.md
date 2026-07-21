# Starter (scrubbed frames, single-file)

**One HTML file. Edit the text. That's it.**

Everything lives in `index.html` — the style, the scroll logic, and every overlay's copy. No CSS or JS file to hunt through.

## Steps

**1. Extract frames from your video** (do this once, from the folder that contains `index.html`):

```bash
ffmpeg -i /path/to/source.mp4 \
  -vf "fps=6,scale='min(1920,iw)':-2" -q:v 4 \
  frames/frame_%04d.jpg
```

- `fps=6` → 6 frames per second of source. 60 seconds of source ≈ 360 frames.
- `-q:v 4` → editorial JPG quality (~150 KB per frame at 1080p).
- Files land as `frames/frame_0001.jpg`, `frames/frame_0002.jpg`, ...

**2. Set the frame count.** Open `index.html`, find:

```js
const FRAME_COUNT = 360;
```

Change `360` to however many JPGs actually landed in `frames/`. Verify with `ls frames | wc -l`.

**3. Edit the overlays.** Scroll down in `index.html` until you find the six `<div class="overlay">` blocks between the marked `EDIT OVERLAY TEXT + TIMING HERE` and `SCROLL LOGIC` comments. Change the text, `data-at` (fade in point, 0..1), `data-until` (fade out point, 0..1), and the position class.

**4. Run:**

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## The three things you'll edit

| What | Where in `index.html` |
|---|---|
| Colors, font, scroll pacing | `:root { ... }` at top of `<style>` |
| Overlay text and timing | `<div class="overlay ...">` blocks inside `<main>` |
| Frame count | `const FRAME_COUNT = 360;` inside `<script>` |

## Overlay attributes

```html
<div class="overlay POSITION" data-at="0.20" data-until="0.45">
  <h2>Title</h2>
  <p>Body copy.</p>
</div>
```

- `POSITION`: one of `top-left`, `top-right`, `bottom-left`, `bottom-right`, `center`
- `data-at`: reader-scroll fraction (0..1) at which this fades in
- `data-until`: reader-scroll fraction at which this fades out
- Use `<h1>` for big titles, `<h2>` for section beats, `<p class="byline">` for credits, `<h2 class="stat">` for big data numbers

Overlays can overlap. If you want two things visible at the same time, give them the same `data-at`/`data-until` range and different position classes.

## When it doesn't work

- **All I see is a black screen** — the `frames/` folder is empty or `FRAME_COUNT` is wrong. `ls frames | head -3` and confirm they're named `frame_0001.jpg` etc.
- **Overlays never show** — `data-at` might be `> 1` or `data-until < data-at`. Both must be in `[0, 1]`.
- **Scrolling is slow / laggy** — too many frames or files are too big. Re-run `ffmpeg` with `fps=4` or `-q:v 6`.

## When to graduate

If you find yourself wanting:
- Multiple discrete video clips instead of one continuous scroll → use `../starter/` (scene-per-clip)
- Smaller download and OK with minor mobile jitter → use `../starter-scrub-video/` (single MP4)
- More overlay variety (panels, right-side captions with images) → copy the position classes from `../starter-scrub-frames/assets/css/style.css`
