// ============================================================
// Scrollytelling starter — scroll.js
//
// Two responsibilities:
//   1. Swap the fixed video's `src` when a new scene enters view.
//   2. Turn overlays on/off based on how far the reader has scrolled
//      into each scene (data-at .. data-until, both 0..1).
// ============================================================

(() => {
  const video = document.getElementById('bg-video');
  const scenes = Array.from(document.querySelectorAll('.scene'));
  const progressFill = document.getElementById('progress-fill');

  // ----- 1. Scene → video switching --------------------------------
  // We track which scene is "current" (the one whose midpoint is
  // closest to the viewport midpoint) and swap the video accordingly.
  let currentClip = null;

  function pickCurrentScene() {
    const midpoint = window.innerHeight / 2;
    let bestScene = null;
    let bestDist = Infinity;
    for (const s of scenes) {
      const r = s.getBoundingClientRect();
      const centerDist = Math.abs((r.top + r.bottom) / 2 - midpoint);
      if (centerDist < bestDist) {
        bestDist = centerDist;
        bestScene = s;
      }
    }
    return bestScene;
  }

  function ensureClip(scene) {
    if (!scene) return;
    const clip = scene.dataset.clip;
    if (!clip || clip === currentClip) return;
    currentClip = clip;
    video.src = clip;
    // Some browsers block autoplay until first user interaction.
    // Muted + playsinline + user gesture on scroll usually clears it.
    const p = video.play();
    if (p && p.catch) p.catch(() => { /* silent */ });
  }

  // ----- 2. Overlay activation and scene progress ------------------
  function updateOverlays() {
    for (const scene of scenes) {
      const r = scene.getBoundingClientRect();
      const total = scene.offsetHeight - window.innerHeight;
      // progress = 0 when the scene's top hits the viewport top,
      // progress = 1 when its bottom hits the viewport bottom.
      const progress = total > 0
        ? Math.max(0, Math.min(1, -r.top / total))
        : (r.top < 0 && r.bottom > 0 ? 0.5 : 0);
      scene._progress = progress;

      const overlays = scene.querySelectorAll('.overlay');
      overlays.forEach((o) => {
        const at = parseFloat(o.dataset.at || '0');
        const until = parseFloat(o.dataset.until || '1');
        const on = progress >= at && progress <= until;
        o.classList.toggle('active', on);
      });
    }
  }

  function updateProgressBar() {
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const p = scrollable > 0 ? window.scrollY / scrollable : 0;
    if (progressFill) progressFill.style.width = (p * 100).toFixed(2) + '%';
  }

  // ----- 3. rAF loop ----------------------------------------------
  let ticking = false;
  function tick() {
    ticking = false;
    ensureClip(pickCurrentScene());
    updateOverlays();
    updateProgressBar();
  }
  function requestTick() {
    if (!ticking) { requestAnimationFrame(tick); ticking = true; }
  }

  window.addEventListener('scroll', requestTick, { passive: true });
  window.addEventListener('resize', requestTick);
  document.addEventListener('DOMContentLoaded', requestTick);
  window.addEventListener('load', () => {
    // Prime the video once fonts + layout settle
    requestTick();
    setTimeout(requestTick, 200);
  });

  // Nudge autoplay to start on first touch/scroll for browsers that
  // block muted autoplay in some contexts.
  const unlock = () => {
    video.play().catch(() => {});
    window.removeEventListener('scroll', unlock);
    window.removeEventListener('click', unlock);
    window.removeEventListener('touchstart', unlock);
  };
  window.addEventListener('scroll', unlock, { once: true, passive: true });
  window.addEventListener('click', unlock, { once: true });
  window.addEventListener('touchstart', unlock, { once: true, passive: true });
})();
