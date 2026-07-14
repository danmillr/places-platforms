// assets/js/map.js
// Tutorial 2A: MapLibre GL JS + GeoJSON layers, popups, and layer toggles

/* =============================================================
   INITIALIZE THE MAP
   ============================================================= */

const map = new maplibregl.Map({
  container: "map",
  // CARTO Positron: clean light basemap, no API key required
  // Alternatives: see README for other free tile styles
  style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
  center: [-73.97, 40.72],   // NYC overview — [longitude, latitude]
  zoom: 10.5,
  maxBounds: [            // prevent the user from panning too far from NYC
    [-74.5, 40.4],        // [west, south]
    [-73.5, 41.1],        // [east, north]
  ],
});

// Add navigation controls (zoom buttons + compass)
map.addControl(new maplibregl.NavigationControl(), "top-right");

// Add scale bar in the bottom-left
map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: "imperial" }), "bottom-left");


/* =============================================================
   LOAD DATA AFTER THE MAP IS READY
   The 'load' event fires once the base tiles and style are loaded.
   Always add sources and layers inside this callback.
   ============================================================= */

map.on("load", async () => {

  // ----- Load GeoJSON via fetch -----
  // fetch() works for local files when running on a server (e.g. GitHub Pages).
  // If opening index.html directly from your filesystem (file:// protocol), you'll
  // get a CORS error. Use VS Code's Live Server extension, or run: python3 -m http.server
  let sitesData, areasData;

  try {
    const [sitesRes, areasRes] = await Promise.all([
      fetch("./assets/data/nyc-sites.geojson"),
      fetch("./assets/data/study-areas.geojson"),
    ]);
    sitesData = await sitesRes.json();
    areasData = await areasRes.json();
  } catch (err) {
    console.error("Could not load GeoJSON:", err);
    return;
  }

  // ----- Add sources -----
  // A source is the data. A layer is the visual representation.
  // One source can power multiple layers (e.g. fill + outline).

  map.addSource("sites", {
    type: "geojson",
    data: sitesData,
  });

  map.addSource("study-areas", {
    type: "geojson",
    data: areasData,
  });


  // ----- Study area layers (add first so they appear under points) -----

  map.addLayer({
    id: "study-area-fill",
    type: "fill",
    source: "study-areas",
    paint: {
      "fill-color": "#e05a2b",
      "fill-opacity": 0.12,
    },
  });

  map.addLayer({
    id: "study-area-outline",
    type: "line",
    source: "study-areas",
    paint: {
      "line-color": "#e05a2b",
      "line-width": 2,
      "line-dasharray": [4, 2],
    },
  });


  // ----- Site point layers -----

  map.addLayer({
    id: "sites-circles",
    type: "circle",
    source: "sites",
    paint: {
      // Data-driven radius: scale between zoom levels for visual clarity
      "circle-radius": [
        "interpolate", ["linear"], ["zoom"],
        10, 5,    // at zoom 10, radius = 5px
        15, 12,   // at zoom 15, radius = 12px
      ],
      // Color by category using a match expression
      "circle-color": [
        "match",
        ["get", "category"],
        "Open Space",         "#2E7D32",
        "Waterfront",         "#0277BD",
        "Waterfront / Resilience", "#0277BD",
        "Commercial / Civic", "#3C4ED6",
        "#888888",  // default
      ],
      "circle-stroke-color": "white",
      "circle-stroke-width": 2,
      "circle-opacity": 0.9,
    },
  });

  map.addLayer({
    id: "sites-labels",
    type: "symbol",
    source: "sites",
    minzoom: 12,    // only show labels when zoomed in enough
    layout: {
      "text-field": ["get", "name"],
      "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
      "text-size": 12,
      "text-offset": [0, 1.4],
      "text-anchor": "top",
      "text-max-width": 10,
    },
    paint: {
      "text-color": "#1B1B33",
      "text-halo-color": "rgba(255,255,255,0.9)",
      "text-halo-width": 2,
    },
  });


  // ----- Popups -----
  // Show a popup when clicking a site circle

  map.on("click", "sites-circles", (e) => {
    const feature = e.features[0];
    const props = feature.properties;

    // For Point features, coordinates is [lng, lat]
    const coords = feature.geometry.coordinates.slice();

    // When zoomed out and features overlap, MapLibre may wrap longitude values.
    // This adjustment ensures the popup appears at the correct position.
    while (Math.abs(e.lngLat.lng - coords[0]) > 180) {
      coords[0] += e.lngLat.lng > coords[0] ? 360 : -360;
    }

    new maplibregl.Popup({ offset: 16 })
      .setLngLat(coords)
      .setHTML(`
        <div class="popup-title">${props.name}</div>
        <span class="popup-category">${props.category}</span>
        <div class="popup-desc">
          <strong>${props.neighborhood}</strong>${props.year ? ` &mdash; ${props.year}` : ""}<br/>
          ${props.description}
        </div>
      `)
      .addTo(map);
  });

  // Cursor feedback for clickable features
  map.on("mouseenter", "sites-circles", () => {
    map.getCanvas().style.cursor = "pointer";
  });
  map.on("mouseleave", "sites-circles", () => {
    map.getCanvas().style.cursor = "";
  });


  // ----- Fly-to buttons -----
  // Dynamically create a button in the sidebar for each site

  const flyButtonsEl = document.getElementById("fly-buttons");

  sitesData.features.forEach(feature => {
    const props = feature.properties;
    const btn = document.createElement("button");
    btn.className = "fly-btn";
    btn.textContent = props.name;
    btn.addEventListener("click", () => {
      map.flyTo({
        center: feature.geometry.coordinates,
        zoom: props.zoom || 14,
        bearing: props.bearing || 0,
        pitch: props.pitch || 0,
        duration: 1800,
        essential: true,
      });
    });
    flyButtonsEl.appendChild(btn);
  });

});


/* =============================================================
   LAYER TOGGLE FUNCTION
   Called from the HTML checkboxes via onchange="toggleLayer(...)"
   ============================================================= */

function toggleLayer(layerId) {
  // getLayoutProperty returns "none" if hidden, or undefined/"visible" if shown
  const current = map.getLayoutProperty(layerId, "visibility");
  const next = current === "none" ? "visible" : "none";
  map.setLayoutProperty(layerId, "visibility", next);
}
