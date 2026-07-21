// ============================================================
// Scrubbed frames scrollytelling — scrub.js
//
// Reads: assets/frames/frame_NNNN.jpg  (N frames)
// Behavior:
//   - Preloads all frames on page load.
//   - As reader scrolls, maps scroll progress (0..1) to a frame index.
//   - Swaps <img id="frame">.src to that frame.
//   - Toggles overlay .active based on data-at / data-until (0..1 globally).
//
// EDIT the two constants below to match your extraction.
// ============================================================

const FRAME_COUNT = 360;                 // total number of JPGs in assets/frames/
const FRAME_PATH  = 'assets/frames/';
const FRAME_PREFIX = 'frame_';
const FRAME_PAD = 4;                     // "frame_0001.jpg" -> 4-digit padding
const FRAME_EXT = '.jpg';

(() => {
  const img = document.getElementById('frame');
  const progressFill = document.getElementById('progress-fill');
  const blocks = Array.from(document.querySelectorAll('.overlay-block'));

  // Build frame URLs
  const frameUrl = (i) =>
    FRAME_PATH + FRAME_PREFIX + String(i).padStart(FRAME_PAD, '0') + FRAME_EXT;

  // --- Preload frames in memory --------------------------------
  // We fire off Image() requests so the browser caches them.
  // For >500 frames, consider batching or lazy prefetching.
  const preloaded = new Array(FRAME_COUNT);
  function preload() {
    for (let i = 1; i <= FRAME_COUNT; i++) {
      const im = new Image();
      im.src = frameUrl(i);
      preloaded[i - 1] = im;
    }
  }
  preload();

  // --- Scroll -> frame + overlays ------------------------------
  let currentIdx = -1;

  function onScroll() {
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const p = scrollable > 0 ? window.scrollY / scrollable : 0;
    const idx = Math.max(1, Math.min(FRAME_COUNT, Math.round(p * (FRAME_COUNT - 1)) + 1));
    if (idx !== currentIdx) {
      img.src = frameUrl(idx);
      currentIdx = idx;
    }
    if (progressFill) progressFill.style.width = (p * 100).toFixed(2) + '%';

    for (const b of blocks) {
      const at = parseFloat(b.dataset.at || '0');
      const until = parseFloat(b.dataset.until || '1');
      const on = p >= at && p <= until;
      b.querySelectorAll('.overlay').forEach(o => o.classList.toggle('active', on));
    }
  }

  let ticking = false;
  function requestTick() {
    if (!ticking) {
      requestAnimationFrame(() => { ticking = false; onScroll(); });
      ticking = true;
    }
  }
  window.addEventListener('scroll', requestTick, { passive: true });
  window.addEventListener('resize', requestTick);
  document.addEventListener('DOMContentLoaded', requestTick);
})();
