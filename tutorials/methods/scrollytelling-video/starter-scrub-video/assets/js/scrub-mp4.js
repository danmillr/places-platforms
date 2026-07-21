// ============================================================
// Scrubbed MP4 scrollytelling — scrub-mp4.js
//
// Behavior:
//   - Video is paused; currentTime is set directly from scroll.
//   - Requires an H.264 MP4 encoded with tight keyframes (2s max).
//     See ../README.md for the ffmpeg recipe.
//   - Works well for clips <= ~30 seconds. Longer clips will feel
//     jittery on mobile because keyframe seeking has real latency.
// ============================================================

(() => {
  const video = document.getElementById('bg-video');
  const progressFill = document.getElementById('progress-fill');
  const blocks = Array.from(document.querySelectorAll('.overlay-block'));

  video.pause();

  // Some browsers only start filling the buffer once metadata is loaded.
  let duration = 0;
  video.addEventListener('loadedmetadata', () => {
    duration = video.duration || 0;
    onScroll();
  });

  function onScroll() {
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const p = scrollable > 0 ? window.scrollY / scrollable : 0;

    if (duration && !isNaN(duration)) {
      const t = p * duration;
      // Only seek if the delta is meaningful — avoids continuous re-seeking.
      if (Math.abs(video.currentTime - t) > 0.03) {
        try { video.currentTime = t; } catch (e) { /* seek race, ignore */ }
      }
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
