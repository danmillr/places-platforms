# Starter (scrubbed MP4)

Scroll drives `video.currentTime` directly on a single MP4. Simplest code, smallest download, but browser seek latency limits it to shorter clips.

## Encode your video for smooth seeking

Two things matter: **keyframe interval** and **profile**. Tight keyframes let the browser seek without decoding a long chain of intermediate frames.

```bash
ffmpeg -i source.mp4 -c:v libx264 -crf 22 -preset slow \
  -g 15 -keyint_min 15 -sc_threshold 0 \
  -vf "scale='min(1280,iw)':-2,fps=30" \
  -movflags +faststart -an \
  assets/clips/source.mp4
```

- `-g 15 -keyint_min 15 -sc_threshold 0` — a keyframe every 15 frames (~0.5s at 30fps). This is more aggressive than the scene starter because scrub needs finer keyframe granularity. **File is bigger** than a scene-style clip; expect ~2x the size.
- `-crf 22` — slightly better quality than the scene starter, since users may pause on any frame.
- `-vf "scale='min(1280,iw)':-2,fps=30"` — cap width at 1280 (bandwidth) and force 30fps (predictable seek).
- `-movflags +faststart` — required for progressive streaming.
- `-an` — no audio.

**Target:** under 15 MB total, under 30 seconds of source.

## Length limits

| Video length | Behavior |
|---|---|
| ≤ 10 sec  | Smooth on all browsers and devices |
| 10-30 sec | Smooth on desktop, occasional jitter on mid-range mobile |
| 30-60 sec | Noticeable jitter on mobile; consider frame sequence instead |
| > 60 sec  | Don't. Use `../starter-scrub-frames/` or `../starter/` |

## Then

Drop your encoded file at `assets/clips/source.mp4`, edit `index.html` to change overlays, run:

```bash
python3 -m http.server 8000
```

## When to use this vs frame sequence

Use this starter when:
- Your video is **short** (under 30 seconds).
- You want **the smallest total download**.
- You're OK with occasional micro-jitter on older devices.

Use `../starter-scrub-frames/` when:
- Your video is 30-90 seconds.
- You want **perfectly smooth** scroll response.
- You can accept a larger total download (~50-100 MB of JPGs).
