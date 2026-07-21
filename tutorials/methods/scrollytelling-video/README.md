# Scrollytelling video: scroll-driven video with text and image overlays

**Status: Full.** A working static-site starter is in `starter/`. Copy it into your project directory, drop in your clips, edit `index.html`, deploy to GitHub Pages.

## What you will build

A one-page site that plays a background video and layers text and images over it in response to scroll — the pattern the NYTimes, Pudding, Bloomberg Graphics, and Reuters use for interactive features. The reader scrolls and:

1. The background video swaps from clip to clip as they enter new **scenes**.
2. Text and images fade in and out at scripted moments inside each scene.
3. A slim progress bar at the top tracks how far they've read.

You will start from a 5-6 minute source video, split it into 4-12 clips, and script overlays on top.

## Prerequisites

- A 5-6 minute video (or several separate videos you plan to sequence)
- `ffmpeg` for splitting and compressing clips: `brew install ffmpeg`
- A code editor (VS Code recommended)
- Basic HTML familiarity — you'll be editing `<section>` blocks and their attributes
- No build system, no Node, no framework. Static files served by `python3 -m http.server`.

## Files in this method

```
scrollytelling-video/
├── README.md                      # this file
├── starter/                       # SCENES: multi-clip, looping (recommended)
├── starter-scrub-frames/          # SCRUBBED via JPG frames — NYT-style
└── starter-scrub-video/           # SCRUBBED via single MP4 — smallest
```

Three separate starters, three different scroll-to-video patterns. **Pick one and copy that folder into your project.** They do not compose — you use one or the other. Each starter is self-contained with its own `README.md` explaining the specific edit surface.

### Which starter for what

| Situation | Use this starter |
|---|---|
| 3+ minute source, multiple distinct shots, looping OK | `starter/` (scene-based) |
| Under 90-sec continuous camera move, want reader's scroll to be the "playhead", ≤ 100 MB of frame JPGs is OK | `starter-scrub-frames/` |
| Under 30-sec clip, want the smallest total download, OK with minor mobile jitter | `starter-scrub-video/` |
| Not sure? | `starter/` — safest, works for the widest range of source material |

## Design principle: one config file, everything else invisible

The whole editing surface is `index.html`. Everything else — the CSS layout, the scroll math — is done. Students edit one file: sections, clip filenames, text, images. They add a scene by copy-pasting a `<section>` and changing the `data-*` attributes.

That constraint is deliberate. The moment scrollytelling becomes a per-scene JavaScript authoring problem, students spend their time on plumbing instead of on the argument the piece is making.

## Three scroll-to-video patterns

There are three practical ways to sync scroll to video, and this method ships a starter for each:

1. **Scrubbed video (single MP4)** — `starter-scrub-video/`. `video.currentTime` is directly bound to scroll position. Scrolling drags the playhead through one video. Smallest download. Cinematic, but browsers seek slowly through non-keyframe frames, so mobile stutters above ~30 seconds of source.

2. **Scrubbed frame sequence (JPG)** — `starter-scrub-frames/`. Same scroll-drives-playhead feel, but the "video" is actually N pre-extracted JPGs and scroll swaps `<img>.src`. Perfectly smooth in every browser (it's just image loading), no decode work. This is what NYTimes uses for "scroll to fly the drone" pieces. Downside: total download of 30-100 MB of JPGs.

3. **Scene-per-clip** — `starter/`. Split the source into short clips, one per scene. When a scene enters view, its clip loads into a shared `<video>` element and autoplays looped. Scroll timing is decoupled from clip timing (each clip loops silently), so a reader who lingers still sees relevant footage, and a reader who skims doesn't miss key frames. Works for source video of any length. This is what most editorial scrollytelling pieces do in 2024-2026 when they have multiple shots to sequence.

**They are separate starters.** Copy the one that fits and edit inside it. Below, the walkthrough covers pattern 3 (scene-per-clip); patterns 1 and 2 have their own edit surfaces documented in each starter's own README.

## First run in five minutes

If you just want to see the starter working before you have your own video:

```bash
cp -R tutorials/methods/scrollytelling-video/starter my-piece
cd my-piece

# Drop any short .mp4 you already have (a phone recording works fine) as all
# four clips, so every scene has something to play:
cp ~/path/to/any-short-video.mp4 assets/clips/01_opening.mp4
cp assets/clips/01_opening.mp4 assets/clips/02_scene.mp4
cp assets/clips/01_opening.mp4 assets/clips/03_data.mp4
cp assets/clips/01_opening.mp4 assets/clips/04_close.mp4

python3 -m http.server 8000
# open http://localhost:8000
```

Scroll and confirm: overlays fade in/out, the clip plays, the progress bar fills. Now open `index.html` and start editing.

## How the pieces fit together

Three files, three concerns:

- **`index.html`** — the *content and timing* layer. You edit this to say *what* text and images appear *when*. Everything a student edits day-to-day is here.
- **`assets/css/style.css`** — the *look* layer. Colors, fonts, spacing, transitions. Editable but doesn't need to be for a first pass.
- **`assets/js/scroll.js`** — the *plumbing*. Watches scroll position, decides which scene is current, tells the video to swap clips, toggles the `.active` class on overlays. You should not need to edit this.

The data flow, top to bottom:

1. Reader scrolls.
2. `scroll.js` picks the scene whose vertical midpoint is closest to the viewport midpoint.
3. If that scene's `data-clip` is different from the current video source, `scroll.js` sets `video.src` and calls `.play()`.
4. For every scene, `scroll.js` computes `progress` (0..1) — how far into the scene the reader has scrolled.
5. For every `.overlay` inside a scene, `scroll.js` checks whether `progress` is between the overlay's `data-at` and `data-until`. If yes, add class `active`.
6. CSS transitions `opacity` and `transform` on `.active` — the overlay fades in.

That's the whole system. If something misbehaves, the first place to look is those numbers.

## Walkthrough

### 1. Copy the starter into your project

```bash
cp -R tutorials/methods/scrollytelling-video/starter my-project
cd my-project
python3 -m http.server 8000
# open http://localhost:8000
```

You should see the starter scenes with placeholder text. The video area will be black until you add clips (next step).

### 2. Split your source video into clips

Aim for **4-12 clips**, each **20-60 seconds** long. One clip = one scene = one "moment" of your story. Clips are meant to loop while the reader lingers, so pick self-contained shots that read well on repeat.

#### Planning your cuts

Before you touch `ffmpeg`, watch the 6-minute source and write a two-column table:

| Time in / out | Scene name | What the reader is doing here |
|---|---|---|
| 0:00 – 0:32 | Opening | Meeting the place. Big statement of what the piece is about. |
| 0:32 – 1:25 | Sound / senses | Introducing the sensory frame of the argument. |
| 1:25 – 2:10 | A data point | Anchoring the argument with one specific number. |
| ... | ... | ... |

Then translate each row into an `ffmpeg` command below.

#### ffmpeg cookbook

**Basic split (single clip at explicit seconds):**

```bash
ffmpeg -i source.mp4 -ss 0 -to 32 \
  -c:v libx264 -crf 24 -preset slow \
  -vf "scale='min(1920,iw)':-2" \
  -movflags +faststart -an \
  my-project/assets/clips/01_opening.mp4
```

**All clips at once (bash loop):**

```bash
# times: (start end name), all in seconds
cuts=(
  "0    32    01_opening"
  "32   85    02_sound"
  "85   130   03_data"
  "130  180   04_close"
)
for c in "${cuts[@]}"; do
  read start end name <<< "$c"
  ffmpeg -i source.mp4 -ss "$start" -to "$end" \
    -c:v libx264 -crf 24 -preset slow \
    -vf "scale='min(1920,iw)':-2" \
    -movflags +faststart -an \
    "my-project/assets/clips/${name}.mp4"
done
```

**Cap width at 1280 (smaller files for slower networks):**

```bash
-vf "scale='min(1280,iw)':-2"
```

**Force keyframes every 2 seconds (smoother loops and seeks):**

```bash
-c:v libx264 -crf 24 -preset slow -g 60 -keyint_min 60
```

**Make a clip loop seamlessly by crossfading end-to-start:**

```bash
# 1s crossfade in the last second of the clip
ffmpeg -i input.mp4 -filter_complex \
  "[0:v]trim=0:31,setpts=PTS-STARTPTS[a]; \
   [0:v]trim=31:32,setpts=PTS-STARTPTS[b]; \
   [0:v]trim=0:1,setpts=PTS-STARTPTS[c]; \
   [b][c]xfade=transition=fade:duration=1:offset=0[end]; \
   [a][end]concat=n=2:v=1:a=0[out]" \
  -map "[out]" -c:v libx264 -crf 24 -preset slow -movflags +faststart -an output.mp4
```

#### Flag guide

- `-c:v libx264 -crf 24 -preset slow` — H.264 at good quality, small file. Lower CRF = higher quality. **18** = archival, **24** = editorial, **28** = mobile-friendly. Stay in 20-28 for the web.
- `-vf "scale='min(1920,iw)':-2"` — cap at 1080p width (video is a background; more is wasted bytes). The `-2` on height keeps aspect ratio and forces even dimensions.
- `-movflags +faststart` — moves the MP4 index to the front so playback starts before the whole file downloads. **Required** for web streaming.
- `-an` — strips audio (the video is muted for autoplay anyway; deleting the audio track saves ~1MB per clip).
- `-preset slow` — trades encode time for file size. Use `slow` for final export, `fast` while iterating.
- `-g 60 -keyint_min 60` — a keyframe every 60 frames (2s at 30fps). Enables tighter seeking and cleaner loop points at a small file-size cost.

#### Target file sizes

| Clip length | Target size | Typical bitrate |
|---|---|---|
| 20 seconds | 4-8 MB | ~2-3 Mbps |
| 30 seconds | 6-12 MB | ~2 Mbps |
| 60 seconds | 10-20 MB | ~1.5-2 Mbps |

Larger than that and mobile users will see loading pauses at scene boundaries. Total for all clips should stay under ~100 MB for GitHub Pages hosting; over that, host videos on Cloudflare R2, S3, or Bunny.net (see "Deploy" below).

#### Same aspect ratio, always

If your source shots have different aspect ratios (say a 16:9 interview cut together with a 9:16 phone recording), the video area will jump between them because `object-fit: cover` re-crops each new source. Options:

- Pre-crop everything to a shared aspect ratio in ffmpeg (`-vf "crop=..."`).
- Or leave the jump as an intentional beat between scenes.
- Or letterbox the odd-shaped ones onto a black canvas of the majority aspect.

### 3. Edit `index.html` — scenes and overlays

Open `index.html`. Each `<section class="scene">` is one scene. Structure:

```html
<section class="scene" data-clip="assets/clips/02_scene.mp4" data-label="Sound">

  <div class="overlay title center" data-at="0.05" data-until="0.35">
    <h2>Every 3 minutes</h2>
  </div>

  <div class="overlay caption bottom-left" data-at="0.35" data-until="0.75">
    <p>A caption appears later, layered over the same clip.</p>
  </div>

  <div class="overlay right-panel" data-at="0.45" data-until="0.95">
    <img src="assets/img/subway_diagram.png" alt="" />
    <p class="label">Photo credit</p>
  </div>

</section>
```

Attributes to know:

| Attribute | Where | What it does |
|---|---|---|
| `data-clip` | on `<section>` | path to the clip that plays while this scene is on screen |
| `data-label` | on `<section>` | optional; not shown to reader, useful for you |
| `data-at` | on `<div class="overlay">` | fraction of scene progress (0..1) at which the overlay fades in |
| `data-until` | on `<div class="overlay">` | fraction of scene progress at which the overlay fades out |
| `class="overlay ..."` | on `<div>` | overlay position + variant. See position classes below. |

**Position classes** (pick one per overlay):
- `top-left`, `top-right`, `bottom-left`, `bottom-right` — corners
- `center` — dead center, centered text
- `left-panel`, `right-panel` — vertical panels along the side, good for image + caption pairs

**Content classes** (optional, combinable):
- `title` — larger, tighter type
- `caption` — smaller, italic-ish, sits close to a corner
- `label` — tiny credit-line style
- `.stat` on an `h2` — huge accent-color number for a data point

### 4. Tune when overlays appear

`data-at` and `data-until` are fractions of **that scene's scroll progress**, not clock time. A scene is 220vh tall by default (change `--scene-height` in `style.css`). So:

- `data-at="0.10"` = fade in when the reader is 10% into scrolling this scene
- `data-until="0.90"` = fade out at 90%

Layering rules of thumb:

- Give each overlay a range of ~30-50% of the scene, so it lingers.
- Overlaps are fine: two overlays can both be `active` at the same time (a title + a caption below it).
- The last `data-until` in a scene should be `<= 0.95` so the overlay is gone before the next scene enters.
- Overlay content longer than the range will get cut off mid-read. Give slower text more scroll room (`data-until - data-at >= 0.4`).

#### Overlay class cheat-sheet

Position (pick one):

| Class | Where the overlay sits |
|---|---|
| `top-left` | top-left corner |
| `top-right` | top-right corner (right-aligned text) |
| `bottom-left` | bottom-left corner |
| `bottom-right` | bottom-right corner (right-aligned text) |
| `center` | dead-center, centered text |
| `left-panel` | vertical panel along the left edge; good for image + caption pairs |
| `right-panel` | vertical panel along the right edge |

Content variants (combinable):

| Class | Purpose |
|---|---|
| `title` | larger, tighter type, use for scene titles |
| `caption` | smaller body copy for a paragraph |
| `label` | tiny credit-line style, add on `<p>` after an image |

Specials:

| Class | Purpose |
|---|---|
| `stat` (on `<h2>`) | huge accent-color number for a data point |

#### Editing recipes

**A section title that stays put through the scene:**

```html
<div class="overlay title top-left" data-at="0.05" data-until="0.95">
  <h2>The pier at 3pm</h2>
</div>
```

**A quote that fades in, then leaves before the next thought:**

```html
<div class="overlay center" data-at="0.30" data-until="0.65">
  <h2>"They said it was temporary."</h2>
  <p>— Resident, interviewed 2024</p>
</div>
```

**A photo panel with caption that lives to the right for most of the scene:**

```html
<div class="overlay right-panel" data-at="0.20" data-until="0.90">
  <img src="assets/img/facade_2011.jpg" alt="Storefront in 2011" />
  <p class="label">120 Mott St, 2011. Photo: Google Street View</p>
</div>
```

**Two panels compared side by side (before/after):**

```html
<div class="overlay left-panel" data-at="0.15" data-until="0.85">
  <img src="assets/img/before.jpg" alt="Before" />
  <p class="label">2011</p>
</div>
<div class="overlay right-panel" data-at="0.20" data-until="0.85">
  <img src="assets/img/after.jpg" alt="After" />
  <p class="label">2024</p>
</div>
```

**A "big number" data point that hits hard, then fades:**

```html
<div class="overlay top-right" data-at="0.10" data-until="0.70">
  <h2 class="stat">62%</h2>
  <p>of surveyed storefronts have changed hands since 2015.</p>
</div>
```

**Sequential reveals inside one scene (three beats):**

```html
<section class="scene" data-clip="assets/clips/06_argument.mp4">
  <div class="overlay title center" data-at="0.05" data-until="0.30">
    <h2>First, the observation.</h2>
  </div>
  <div class="overlay title center" data-at="0.32" data-until="0.60">
    <h2>Then, the mechanism.</h2>
  </div>
  <div class="overlay title center" data-at="0.62" data-until="0.92">
    <h2>Finally, the consequence.</h2>
  </div>
</section>
```

Note the tiny gaps (`0.30 -> 0.32`, `0.60 -> 0.62`) so the fade-out completes cleanly before the next fade-in starts.

### 5. Swap in your own images

Drop images into `assets/img/`. In an overlay:

```html
<div class="overlay right-panel" data-at="0.3" data-until="0.85">
  <img src="assets/img/facade_before_after.jpg" alt="Storefront before and after" />
  <p class="label">120 Mott St, 2011 vs 2024. Photos: Google Street View</p>
</div>
```

Panels cap image width at ~380px. Export images at 2× (760px wide) for crisp retina rendering. Prefer JPEG 78-85 or WebP.

### 6. Restyle to match your project

Everything visual is in `assets/css/style.css`. Top of the file:

```css
:root {
  --scene-height: 220vh;   /* longer scenes = slower reveal */
  --brand-bg:     #0f0e14; /* video letterbox background */
  --brand-fg:     #f5f2ea;
  --brand-accent: #e2a000; /* progress bar + .stat numbers */
  --font-body:    'Inter', ...;
  --font-display: 'Inter', ...;
  --gutter:       6vw;
  --overlay-max:  520px;
}
```

Load a webfont in `<head>`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap" rel="stylesheet" />
```

Rules to consider, in order:

1. **One typeface, at most two weights.** Regular for body, bold for titles.
2. **Restrained palette.** Background + foreground + one accent. That is enough.
3. **Whitespace.** Larger gutter (`--gutter: 8vw` on desktop) reads more editorial.
4. **Text shadow only if the video is bright.** The starter includes a light vignette to help.
5. **Do not autoplay any hover animations.** The scroll is already doing work.

#### Palette + typeface pairings that work

Try one of these before iterating on your own:

| Palette name | Background | Foreground | Accent | Font pairing suggestion |
|---|---|---|---|---|
| Editorial dark | `#0f0e14` | `#f5f2ea` | `#e2a000` | Inter or IBM Plex Sans, 400 + 700 |
| Editorial light | `#f6f4ee` | `#111` | `#c72d1a` | EB Garamond (display) + Inter (body) |
| Cool press | `#131820` | `#eae6db` | `#5aa9e6` | IBM Plex Sans, 400 + 600 |
| Warm archive | `#1b1108` | `#efe2c9` | `#e0b544` | Cormorant Garamond + Inter |
Copy the six values into the `:root` variables, load the fonts, done.

#### Adjusting scene pacing

- **Slower reveal** → increase `--scene-height` (e.g. `280vh`). Reader scrolls farther per scene, overlays linger longer.
- **Faster clip** → decrease `--scene-height` (e.g. `160vh`). Punchier, more like a slide deck.
- **Different pacing per scene** → set the CSS variable inline on a `<section>`: `<section class="scene" style="--scene-height: 300vh" ...>`.

### 7. Add an intro and an ending (recommended, not built-in)

A scrollytelling piece feels unfinished without a proper title card at the top and an ending / credits at the bottom. Neither needs new HTML — just build them as scenes.

**Title card scene** — first `<section>`, keep it short, one long overlay:

```html
<section class="scene" data-clip="assets/clips/00_title.mp4" style="--scene-height: 140vh">
  <div class="overlay title center" data-at="0.05" data-until="0.95">
    <h1>Your Title Here</h1>
    <p class="byline">By your name. Cornell ARCH 6133, Places / Platforms, Summer 2026.</p>
    <p style="opacity:0.7">Scroll to begin.</p>
  </div>
</section>
```

**Ending / credits scene** — last `<section>`:

```html
<section class="scene" data-clip="assets/clips/99_credits.mp4" style="--scene-height: 180vh">
  <div class="overlay center" data-at="0.05" data-until="0.4">
    <h2>Sources</h2>
    <p>Data: NYC PLUTO, Google Street View, MTA GTFS-Realtime. Method: Cornell ARCH 6133.</p>
  </div>
  <div class="overlay center" data-at="0.45" data-until="0.85">
    <h2>Thank you for reading.</h2>
    <p class="byline">your-name.com &nbsp;·&nbsp; @your-handle</p>
  </div>
</section>
```

### 8. Deploy

The output is a static site — no server side. GitHub Pages is the fastest path:

```bash
cd my-project
git init && git add . && git commit -m "scrollytelling initial"
git remote add origin git@github.com:<you>/<repo>.git
git push -u origin main

# In the repo settings on GitHub:
# Pages -> Deploy from a branch -> main -> / (root) -> Save
```

Your site will be at `https://<you>.github.io/<repo>/`.

**Video hosting caveat:** large `.mp4` files (> 25 MB total) push against GitHub's soft limits. If your combined clips exceed ~100 MB, host videos on Cloudflare R2, S3, or Bunny.net (a few dollars/month) and change `data-clip` URLs to their public URLs. GitHub Pages then only serves HTML/CSS/JS.

## Alternative: scrubbed variants (deep dive)

Both scrub starters share the same idea: instead of the video playing on its own, the reader's scroll position IS the playhead. The two differ only in how the frames are delivered.

### Scrubbed MP4 (`starter-scrub-video/`)

One `<video>` element, muted, paused. On every scroll tick:

```js
video.currentTime = scrollProgress * video.duration;
```

The video decoder seeks to that frame. This is minimal code but has a real cost: seeking on H.264 is only fast **between keyframes**. Standard encoding puts keyframes every 2-10 seconds, so if the reader scrolls to a moment between keyframes, the browser has to decode the full chain of intermediate frames. That's what causes jitter.

Fix: encode with **tighter keyframes** — every 15 frames (~0.5s at 30fps).

```bash
ffmpeg -i source.mp4 -c:v libx264 -crf 22 -preset slow \
  -g 15 -keyint_min 15 -sc_threshold 0 \
  -vf "scale='min(1280,iw)':-2,fps=30" \
  -movflags +faststart -an \
  starter-scrub-video/assets/clips/source.mp4
```

This doubles file size but makes seeking smooth. Practical ceiling: **~30 seconds of source**. Any longer and mobile browsers stutter.

### Scrubbed JPG frames (`starter-scrub-frames/`)

Extract the video to a folder of numbered JPGs, one per "step":

```bash
mkdir -p starter-scrub-frames/assets/frames
ffmpeg -i source.mp4 -vf "fps=6,scale='min(1920,iw)':-2" \
  -q:v 4 starter-scrub-frames/assets/frames/frame_%04d.jpg
```

- `fps=6` samples 6 frames per second of source. 60 seconds of source at 6 fps = **360 frames**. Bump to `fps=12` for faster action, drop to `fps=4` for slower scenery.
- `-q:v 4` is editorial-grade JPEG quality (~120-180 KB per frame at 1080p). Raise `-q:v` (6-8) to shrink the folder.
- Files land as `frame_0001.jpg` through `frame_0360.jpg`.

Then update `starter-scrub-frames/assets/js/scrub.js`:

```js
const FRAME_COUNT = 360;  // <— set to the actual number of files
```

On every scroll tick, the JS computes the target frame index and swaps `<img>.src`. Because it's just image loading, the browser does no decode work per frame after the first load. All frames are preloaded on page load (an `Image()` per file), so scroll response is instant thereafter.

Practical ceiling: **~100 MB total frames folder**. At 6 fps and ~150 KB/frame, that's 90 seconds of source. Reduce `-q:v` or `fps` to fit more.

### Comparison

| | Scene-per-clip | Scrubbed MP4 | Scrubbed frames |
|---|---|---|---|
| Starter folder | `starter/` | `starter-scrub-video/` | `starter-scrub-frames/` |
| Source length | any | ≤ 30s | ≤ 90s |
| Total download | 30-100 MB clips | 5-15 MB MP4 | 30-100 MB JPGs |
| Scroll → picture feel | picture plays and loops | picture seeks smoothly (if encoded right) | picture perfectly follows scroll |
| Mobile smoothness | very good | mixed | excellent |
| Cross-browser reliability | very good | good | excellent |
| Editing surface | HTML `<section>`s + overlays | HTML overlays only (no scenes) | HTML overlays only (no scenes) |

### Combining patterns

Nothing stops you from building **two pages**: one page with the scene-based starter for the main piece, one page with a scrubbed-frames starter for an intro sequence or a "scroll through this transformation" moment. They share the same overlay HTML/CSS conventions, so an overlay you author in one starter can be pasted into the other.

## Extensions

- **Scroll-linked animation with anime.js or GSAP:** the starter uses pure CSS transitions for simplicity. If you want scrubbed-to-scroll animations (map lines drawing, chart bars growing) drop in a small `gsap` + `ScrollTrigger` include and animate custom overlays. Do not replace the scene/video logic — augment it.
- **Sidebar + video hybrid (Pudding style):** rebuild `.left-panel` / `.right-panel` overlays as a fixed sidebar and use the video for the main column. Change `object-fit: cover` on the video to `contain` and constrain its container.
- **Map instead of video:** put a MapLibre map in place of the `<video>` element. Overlays become storytelling steps that fly the map to different places. See `tutorials/methods/realtime-subway-positions/` for the MapLibre pattern.
- **Chapter navigation:** add a small right-side nav that lists scenes by `data-label` and jumps to them (`element.scrollIntoView({behavior:'smooth'})`).
- **Analytics:** drop in Plausible or Fathom (one script tag) to see how far readers scroll. Cheap and privacy-respecting.
- **Reduced-motion respected:** the starter already softens transitions if `prefers-reduced-motion: reduce`.

## Common pitfalls

- **Autoplay blocked.** Some browsers block muted autoplay in specific edge cases (low-power mode, background tabs). The starter attempts play on scroll/click/touch as a fallback. If a reader still sees a black frame, they can tap the page once.
- **Big videos.** Anything over 15 MB per clip on a mid-range mobile network will stall. Test on a real phone on a real network before publishing. If clips are heavy, cap width at 1280 and CRF at 26.
- **Same aspect across clips.** If your source shots have different aspect ratios, the video area will jump between them because `object-fit: cover` re-crops each new source. Either pre-crop all clips to a shared aspect or accept the jump as a stylistic beat.
- **Overlay content longer than the range.** A long paragraph inside a 20% `data-at`/`data-until` window will get cut off mid-read. Give slower text more scroll room (`data-until - data-at >= 0.4`).
- **Fixed overlay stacking on mobile.** The starter collapses `left-panel` / `right-panel` to a bottom-anchored panel on small screens so they don't overlap other overlays. If you add new position classes, remember to write the mobile fallback in the `@media (max-width: 720px)` block.
- **Video seek jumps.** When the browser has to seek within a clip (e.g., loop back to start), some codecs stutter. `-preset slow` on `ffmpeg` and forcing keyframes every ~2 seconds (`-g 60 -keyint_min 60`) helps: `-c:v libx264 -crf 24 -preset slow -g 60 -keyint_min 60`.
- **iOS quirks.** iOS Safari requires `playsinline` (already set), `muted`, and prefers `preload="metadata"` or `"auto"`. Do not remove those attributes on the video element.

## Attribution and further reading

The scroll-linked-scene pattern is well-established:

- Bostock, Halsey. *How to Scroll* — NYT R&D
- [Scrollama](https://github.com/russellsamora/scrollama) — a JS library that formalizes the same pattern; drop-in replacement for `scroll.js` if you outgrow the starter
- The Pudding's [scrollytelling explainer](https://pudding.cool/process/how-to-implement-scrollytelling/)

Credit your video source in the site (an About section) and, if you use archival material, cite the archive.
