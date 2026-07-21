# Methods: Final Project Support Tutorials

Reference material for common technical patterns students are using in final projects. Each subdirectory is a self-contained tutorial with a README, working code, and pointers to APIs, libraries, and data sources.

Two directories are fully built out as reference exemplars (one web, one analysis notebook). The other seven are scaffolded with goals, prerequisites, and an implementation outline. Ask for a full build on any of them when you are ready to work through it.

## Index

| Tutorial | Format | Status | Question it answers |
|---|---|---|---|
| [realtime-flight-tracker/](realtime-flight-tracker/) | Web (HTML/JS + MapLibre) | Shell | How do I show live flights arriving at or leaving LaGuardia on a map? |
| [realtime-subway-positions/](realtime-subway-positions/) | Web (HTML/JS + MapLibre) | **Full** | How do I show live NYC subway train positions on a map? |
| [creative-forms/](creative-forms/) | Web (HTML/JS + JSONBin or Sheets) | Shell | How do I collect creative user input on a static site and re-render it in the app? |
| [geolocation-zones/](geolocation-zones/) | Web (HTML/JS + Turf.js) | Shell | How do I change what a site shows depending on whether the visitor is inside a POPS boundary? |
| [collective-traces/](collective-traces/) | Web (HTML/JS + Firebase or Supabase) | Shell | How do I let visitors leave a lasting mark (a changed pixel) on a shared page? |
| [video-foot-traffic/](video-foot-traffic/) | Notebook (Python + YOLO) | Shell | How do I turn a video of the Oculus into foot traffic tracks I can import to Rhino? |
| [mta-turnstile/](mta-turnstile/) | Notebook (Python + pandas) | Shell | How do I work with MTA turnstile / hourly ridership data? |
| [text-game-analytics/](text-game-analytics/) | Web (HTML/JS + D3) | Shell | How do I build a text game that captures user behavior and visualizes it at the end? |
| [chinatown-signs/](chinatown-signs/) | Notebook (Python) | **Full** | How do I extract, analyze, and map signs from Street View facades in Chinatown, and embed their text into 3D word space? |
| [subspotting-scrape/](subspotting-scrape/) | Scripts (Python) | **Full** | How do I recover structured data (CSV + GeoJSON) from a static color-coded infographic like the 2017 Subspotting subway reception map? |
| [scrollytelling-video/](scrollytelling-video/) | Web (HTML/CSS/JS) | **Full** | How do I build a NYTimes-style scroll-driven video piece with text and image overlays as a static site? Three starters: scene-per-clip, scrubbed MP4, and scrubbed JPG frames. |

## Shared conventions

**Web tutorials** follow the pattern established in `tutorials/Web/`: a working `index.html` with `assets/{css,js,data}`, runnable via `python3 -m http.server 8000`, deployable to GitHub Pages.

**Notebook tutorials** follow the pattern of the existing `ARCH6133_*.ipynb` files at the root of `tutorials/`: numbered cells with prose, sample data, and small helper functions. Run in Colab or a local Jupyter kernel.

**Every tutorial has a README** that answers the same six questions in order:
1. What you will build
2. Prerequisites (accounts, keys, packages)
3. Data sources and API notes (with links)
4. Walkthrough (numbered steps with code)
5. Extensions and variations
6. Common pitfalls

## Setup expectations

Before starting any tutorial, students should have:
- A GitHub account and a code editor (VS Code recommended)
- Python 3.10+ with pip, or a Colab account, for the notebook tutorials
- Node is not required for any tutorial in this directory. Everything runs client-side or in Python.

Individual tutorials may require additional keys or accounts (Google Maps, MTA, OpenSky, JSONBin, Firebase, etc.). Each README lists what is needed at the top.

## Deliverable expectations

These tutorials are scaffolds for methods, not final deliverables. Your project should adapt the code, not copy it verbatim. In particular:

- Substitute your own study area, sites, and data.
- Rewrite copy and UI to match the argument of your project.
- Cite APIs and data sources in your final documentation.
- If a tutorial uses a mock feed, replace it with a real feed before submission.
