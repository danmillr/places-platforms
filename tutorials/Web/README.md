# Urban Planning Web Mapping — Course Tutorials

Two self-contained tutorials for building and deploying web-based data visualizations and interactive maps. Each tutorial includes working code templates, annotated JavaScript, and step-by-step setup instructions.

---

## Structure

```
course-repo/
├── tutorial-1-static-site/         ← HTML/CSS/JS + GitHub Pages + APIs
│   ├── README.md                   ← Tutorial instructions
│   ├── index.html                  ← Complete working template
│   └── assets/
│       ├── css/style.css
│       └── js/main.js
│
└── tutorial-2-maps-scrollytelling/ ← MapLibre GL JS + GeoJSON + Scrollytelling
    ├── README.md                   ← Tutorial instructions
    ├── index.html                  ← Part A: interactive map with layers
    ├── scrollytelling.html         ← Part B: scrollytelling narrative
    └── assets/
        ├── css/
        │   ├── map.css
        │   └── scrolly.css
        ├── js/
        │   ├── map.js
        │   └── scrolly.js
        └── data/
            ├── nyc-sites.geojson   ← 5 NYC public space sites (points)
            └── study-areas.geojson ← 2 study area polygons
```

---

## Tutorial 1: Static Site + APIs

**File:** `tutorial-1-static-site/`

Covers:
- Setting up a file/folder structure for a static site
- Hosting on GitHub Pages (step-by-step)
- HTML and CSS templates with responsive layout
- Three JavaScript API integrations:
  - **Google Street View** (embedded panorama, requires Maps JS API key)
  - **Open-Meteo** (live weather data, no key required)
  - **MTA GTFS-RT** (subway arrivals, mock data with notes on connecting the live feed)
- API key security and CORS concepts
- Common GitHub Pages deployment pitfalls

**To run locally:**
Open a terminal in the `tutorial-1-static-site/` folder and run:
```bash
python3 -m http.server 8000
# then open http://localhost:8000 in your browser
```
(Opening `index.html` directly as a `file://` URL will cause CORS errors on the API calls.)

---

## Tutorial 2: MapLibre GL JS Maps + Scrollytelling

**File:** `tutorial-2-maps-scrollytelling/`

Covers:
- MapLibre GL JS setup (CDN, no npm needed)
- Free basemap tile providers (no API key)
- GeoJSON format: structure, coordinate conventions, creating and sourcing data
- Adding sources and layers: circles, fills, lines, labels
- Data-driven styling with MapLibre expressions
- Click popups and cursor feedback
- Layer toggle controls
- `flyTo` and `fitBounds` for programmatic map navigation
- **Part B: Scrollytelling**
  - Sticky map + scrolling narrative layout (CSS)
  - `IntersectionObserver` for detecting active panel
  - Syncing `flyTo` animations to scroll position
  - Highlighting active features per step
  - Popup timing relative to flight animations

**Sites explored in the narrative:**
1. The High Line (Chelsea)
2. Times Square Broadway Plazas (Midtown)
3. Domino Park (Williamsburg)
4. Hunters Point South Park (Long Island City)
5. Prospect Park (Brooklyn)

**To run locally:**
```bash
cd tutorial-2-maps-scrollytelling
python3 -m http.server 8000
# Part A: http://localhost:8000/index.html
# Part B: http://localhost:8000/scrollytelling.html
```

---

## Prerequisites

- A GitHub account (free)
- A code editor — [VS Code](https://code.visualstudio.com/) is recommended
- For Tutorial 1 Street View: a Google Maps API key ([get one here](https://console.cloud.google.com))
- For Tutorial 1 transit live feed (optional): an MTA API key ([sign up here](https://api.mta.info/#/signup))

---

## Common Issues

**"My changes aren't showing on GitHub Pages."**
GitHub Pages can cache aggressively. Wait 1-2 minutes and hard-refresh (`Ctrl+Shift+R` / `Cmd+Shift+R`).

**"I'm getting CORS errors when opening HTML files directly."**
Use `python3 -m http.server` or VS Code's Live Server extension. GeoJSON files and some APIs require an HTTP server context.

**"The map isn't loading."**
Check the browser console (F12 → Console). A 404 on a GeoJSON file or a missing library will prevent the map from rendering.

**"Paths work locally but break on GitHub Pages."**
GitHub Pages is case-sensitive. Ensure all filenames and folder names are lowercase and match exactly.
