# Tutorial 2: Web Maps with MapLibre GL JS — GeoJSON, Layers, and Scrollytelling

This tutorial covers two things: how to build an interactive web map with MapLibre GL JS and GeoJSON data, and how to extend that into a scrollytelling narrative that guides readers through specific sites in New York City.

MapLibre GL JS is a community-maintained, open-source fork of Mapbox GL JS. It renders vector tiles on a WebGL canvas, which means smooth pan/zoom, 3D terrain, and no API key required (for many tile providers).

---

## What You'll Build

**Part A:** An interactive map that loads GeoJSON layers (points, polygons, lines) with popups, layer toggles, and custom styling.

**Part B:** A scrollytelling narrative that "flies" the map to five NYC sites as the user scrolls, with supporting text panels that update in sync.

---

## Prerequisites

- Completed Tutorial 1 (you understand HTML/CSS/JS and GitHub Pages deployment)
- A code editor (VS Code recommended)
- Basic comfort with JSON

---

## Part 1: MapLibre GL JS Basics

### Installing / loading the library

You don't need npm for a static site. Load MapLibre from the CDN:

```html
<!-- In <head> -->
<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.5.0/dist/maplibre-gl.css" />

<!-- At bottom of <body>, before your script -->
<script src="https://unpkg.com/maplibre-gl@4.5.0/dist/maplibre-gl.js"></script>
```

Use a pinned version (e.g. `4.5.0`) rather than `@latest` so your site doesn't break when the library updates.

### The minimum map

```html
<div id="map" style="width: 100%; height: 500px;"></div>
<script>
const map = new maplibregl.Map({
  container: "map",           // the DOM element id
  style: "https://demotiles.maplibre.org/style.json",  // free tile style, no key
  center: [-73.9857, 40.7484],  // [longitude, latitude]  (NYC: Times Square)
  zoom: 13,
});
</script>
```

**Coordinate order is [longitude, latitude] throughout MapLibre.** This is the opposite of many APIs (like Google Maps) and is a common gotcha.

### Free tile styles (no API key needed)

| Style | URL |
|-------|-----|
| MapLibre demo (basic) | `https://demotiles.maplibre.org/style.json` |
| OpenFreeMap Positron | `https://tiles.openfreemap.org/styles/positron` |
| OpenFreeMap Liberty | `https://tiles.openfreemap.org/styles/liberty` |
| CARTO Voyager | `https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json` |
| CARTO Dark Matter | `https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json` |

For urban analysis, CARTO Positron or Voyager are clean and readable. Dark Matter works well for data-heavy visualizations.

---

## Part 2: GeoJSON

GeoJSON is a standard JSON format for geographic features. A complete file looks like:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-73.9857, 40.7484]
      },
      "properties": {
        "name": "Times Square",
        "category": "commercial",
        "year_built": null
      }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [-73.9900, 40.7450],
          [-73.9800, 40.7450],
          [-73.9800, 40.7520],
          [-73.9900, 40.7520],
          [-73.9900, 40.7450]
        ]]
      },
      "properties": {
        "name": "Midtown Study Area",
        "area_sqft": 240000
      }
    }
  ]
}
```

Key rules:
- Coordinates are always `[longitude, latitude]` (and optionally altitude as a third value)
- Polygon rings must **close** (first and last coordinate identical)
- Polygon rings must be **counterclockwise** for the outer ring (clockwise for holes)
- All properties values can be strings, numbers, booleans, or null

Good tools for creating GeoJSON: [geojson.io](https://geojson.io) (draw in browser), [QGIS](https://qgis.org) (export any dataset), or write it by hand for simple point datasets.

---

## Part 3: Adding GeoJSON Layers to MapLibre

MapLibre uses a **source + layer** model. You add a data source, then add one or more visual layers that reference it.

```javascript
// Wait until the map has loaded its base tiles before adding data.
// Always put your data-loading code inside the 'load' event.
map.on("load", () => {

  // --- Add a GeoJSON source ---
  // The source holds the data. Layers display it.
  map.addSource("my-points", {
    type: "geojson",
    data: "./assets/data/sites.geojson",  // local file path, or a URL
  });

  // --- Add a circle layer (for Point geometries) ---
  map.addLayer({
    id: "sites-circles",     // unique id, used to reference this layer later
    type: "circle",
    source: "my-points",     // must match the source id above
    paint: {
      "circle-radius": 8,
      "circle-color": "#3C4ED6",
      "circle-stroke-color": "white",
      "circle-stroke-width": 2,
      "circle-opacity": 0.85,
    },
  });

  // --- Add a symbol layer (for labels) ---
  map.addLayer({
    id: "sites-labels",
    type: "symbol",
    source: "my-points",
    layout: {
      "text-field": ["get", "name"],   // reads the "name" property from each feature
      "text-offset": [0, 1.2],         // offset label below the circle
      "text-anchor": "top",
      "text-size": 12,
    },
    paint: {
      "text-color": "#1B1B33",
      "text-halo-color": "white",
      "text-halo-width": 2,
    },
  });

  // --- Add a polygon layer (for Polygon geometries) ---
  map.addSource("study-area", {
    type: "geojson",
    data: "./assets/data/study-area.geojson",
  });

  map.addLayer({
    id: "study-area-fill",
    type: "fill",
    source: "study-area",
    paint: {
      "fill-color": "#3C4ED6",
      "fill-opacity": 0.15,
    },
  });

  map.addLayer({
    id: "study-area-outline",
    type: "line",
    source: "study-area",
    paint: {
      "line-color": "#3C4ED6",
      "line-width": 2,
      "line-dasharray": [4, 2],   // dashed outline
    },
  });

});
```

### Layer ordering

Layers render in the order they are added. Add fills before circles before labels so points appear on top.

### Data-driven styling

MapLibre's paint properties support expressions that read from feature properties. This is how you make a choropleth or scale points by an attribute:

```javascript
// Circle radius based on a property
"circle-radius": ["interpolate", ["linear"], ["get", "capacity"], 0, 4, 1000, 20],
//                ^expression     ^scale type   ^property           min   max

// Color based on a category property
"circle-color": [
  "match",
  ["get", "category"],
  "park",       "#4CAF50",
  "commercial", "#3C4ED6",
  "residential","#FF9800",
  "#999999"     // default fallback
],
```

---

## Part 4: Popups and Interactivity

```javascript
// Show a popup when a circle is clicked
map.on("click", "sites-circles", (e) => {
  // e.features is an array of features under the click point
  const feature = e.features[0];
  const { name, category, description } = feature.properties;

  // Coordinates of the clicked feature
  const coords = feature.geometry.coordinates.slice();  // .slice() avoids mutating the original

  new maplibregl.Popup()
    .setLngLat(coords)
    .setHTML(`
      <strong>${name}</strong><br/>
      <em>${category}</em><br/>
      ${description || ""}
    `)
    .addTo(map);
});

// Change cursor to pointer when hovering a clickable layer
map.on("mouseenter", "sites-circles", () => {
  map.getCanvas().style.cursor = "pointer";
});
map.on("mouseleave", "sites-circles", () => {
  map.getCanvas().style.cursor = "";
});
```

### Layer toggles

```javascript
function toggleLayer(layerId) {
  const visibility = map.getLayoutProperty(layerId, "visibility");
  // If it's "visible" (or undefined, which defaults to visible), hide it. Otherwise show it.
  if (visibility === "none") {
    map.setLayoutProperty(layerId, "visibility", "visible");
  } else {
    map.setLayoutProperty(layerId, "visibility", "none");
  }
}
```

---

## Part 5: Flying the Map Programmatically

The `flyTo` and `fitBounds` methods are the core of scrollytelling animations.

```javascript
// Fly to a specific point with a zoom, bearing, and pitch
map.flyTo({
  center: [-73.9857, 40.7484],  // [lng, lat]
  zoom: 15,
  bearing: -20,      // map rotation in degrees (0 = north up)
  pitch: 45,         // tilt in degrees (0 = top-down, 60 = dramatic perspective)
  duration: 2000,    // animation duration in milliseconds
  essential: true,   // don't skip the animation on reduced-motion settings
});

// Fit the map to a bounding box (useful for showing an area)
map.fitBounds(
  [
    [-74.02, 40.68],  // [west, south]
    [-73.91, 40.80],  // [east, north]
  ],
  {
    padding: 60,       // padding in pixels around the bounds
    duration: 1800,
  }
);
```

---

## Part 6: The Scrollytelling Pattern

Scrollytelling syncs the map view with a scrolling text narrative. The core idea:

1. The map is **fixed** (sticky) on one side of the screen
2. Narrative text panels scroll on the other side
3. As each panel scrolls into the viewport, it triggers a `flyTo` on the map

### The Intersection Observer API

The `IntersectionObserver` fires a callback when elements enter or leave the viewport. This is the right tool for detecting which narrative panel is currently visible.

```javascript
// Create an observer that fires when a panel is more than 50% visible
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      // Get the step index from a data attribute on the panel
      const stepIndex = parseInt(entry.target.dataset.step);
      onStepEnter(stepIndex);
    }
  });
}, {
  threshold: 0.5,   // fire when 50% of the element is visible
});

// Observe every narrative panel
document.querySelectorAll(".narrative-step").forEach(el => observer.observe(el));
```

### Step data structure

Define your narrative steps as a JavaScript array. Each step contains the map view parameters and the text content.

```javascript
const steps = [
  {
    title: "Introduction",
    text: "New York City's public spaces have been shaped by decades of planning decisions...",
    center: [-74.006, 40.712],
    zoom: 11,
    bearing: 0,
    pitch: 0,
  },
  {
    title: "The High Line",
    text: "The High Line transformed an abandoned freight rail line into one of the most visited parks in the world...",
    center: [-74.0048, 40.7480],
    zoom: 15.5,
    bearing: -29,
    pitch: 50,
  },
  // ... more steps
];
```

---

## File Structure for Tutorial 2

```
tutorial-2-maps-scrollytelling/
├── index.html                          ← Part A: basic MapLibre map
├── scrollytelling.html                 ← Part B: full scrollytelling narrative
├── assets/
│   ├── css/
│   │   ├── map.css
│   │   └── scrolly.css
│   ├── js/
│   │   ├── map.js
│   │   └── scrolly.js
│   └── data/
│       ├── nyc-sites.geojson           ← point data for narrative sites
│       └── study-areas.geojson         ← polygon data (optional)
```

---

## Tips for Working with GeoJSON Data

**Finding existing NYC open data in GeoJSON:**
- [NYC Open Data](https://opendata.cityofnewyork.us) (export any dataset as GeoJSON)
- [NYC Planning BYTES of the Big Apple](https://www.nyc.gov/site/planning/data-maps/open-data.page) (authoritative zoning, land use)
- [US Census TIGER files](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) (census tracts, blocks)

**Converting formats:**
- Shapefile to GeoJSON: `ogr2ogr -f GeoJSON output.geojson input.shp` (requires GDAL)
- CSV with lat/lng to GeoJSON: use [csv2geojson](https://github.com/mapbox/csv2geojson) or write a short Python script
- Simplify large polygons: [mapshaper.org](https://mapshaper.org) (reduces file size dramatically for complex shapes)

**Keeping file sizes reasonable:**
- GeoJSON files over ~2MB will slow your page load
- For large datasets, consider [MBTiles](https://docs.mapbox.com/help/glossary/mbtiles/) served from a tile server, or PMTiles (a single-file tile format that can be served from a CDN)
- Simplify geometry in mapshaper if polygons are more detailed than needed at your zoom level

---

## Resources

- [MapLibre GL JS Docs](https://maplibre.org/maplibre-gl-js/docs/)
- [MapLibre Examples Gallery](https://maplibre.org/maplibre-gl-js/docs/examples/)
- [GeoJSON Specification](https://geojson.org/)
- [geojson.io](https://geojson.io) — draw and edit GeoJSON in the browser
- [OpenFreeMap](https://openfreemap.org/) — free tile hosting
- [Scrollama.js](https://github.com/russellsamora/scrollama) — a popular scrollytelling helper library (optional but convenient)
