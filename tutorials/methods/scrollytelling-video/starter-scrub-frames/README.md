# Starter (scrubbed frames)

Scroll drives a **frame sequence**, one JPG per step. Reliable across browsers because it's just image loading. Use this when you want the classic NYTimes / Bloomberg "the reader scrolls and the picture moves" feel.

## Extract frames from your video

```bash
mkdir -p assets/frames

# 6 fps sampling of a 60-second clip = 360 frames
ffmpeg -i source.mp4 -vf "fps=6,scale='min(1920,iw)':-2" \
  -q:v 4 assets/frames/frame_%04d.jpg
```

Trade-offs:
- **Frame rate (fps).** 6 fps feels smooth for slow scenery, 12 fps for movement, 24 fps only if scroll speed will match true frame timing. Higher fps = more files = bigger download.
- **JPEG quality (`-q:v`).** 2 = archival, 4 = editorial (~150 KB/frame at 1080p), 6 = mobile-friendly (~80 KB/frame).
- **Resolution.** Cap at 1920 or 1280 wide. Frames are `object-fit: cover` — anything larger is wasted.

Aim for a **total frames folder size under 100 MB**. If yours is over, drop fps or quality.

## Then

Edit `assets/js/scrub.js` and set `FRAME_COUNT` to the exact number of files you extracted (`ls assets/frames | wc -l`).

Edit `index.html` to change your overlays. `data-at` and `data-until` are **fractions of the full page scroll**, not per-scene — because there are no scenes here, just one scrubbed sequence.

Run:

```bash
python3 -m http.server 8000
```

## When to use this vs the scene starter

Use this starter when:
- Your video is **one continuous camera move** (drone shot, tracking shot, timelapse) and you want the reader's scroll to be the "playhead."
- You want **precise pause-on-scroll** control.
- Your total content is short (under 60-90 seconds of raw video).

Use `../starter/` (scene-based) when:
- You have **multiple distinct shots**.
- You want each shot to loop while the reader lingers.
- Your source is 3+ minutes.
