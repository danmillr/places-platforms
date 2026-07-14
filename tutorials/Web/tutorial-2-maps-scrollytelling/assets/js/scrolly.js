// assets/js/scrolly.js
// Tutorial 2B: Scrollytelling — wires narrative panels to MapLibre map views
// Uses the Intersection Observer API (no external libraries needed)

/* =============================================================
   STEP CONFIGURATION
   Each step defines the map view to fly to when it becomes active.
   The index matches the data-step attribute on the HTML .step elements.
   ============================================================= */

const STEPS = [
  // Step 0: Introduction — NYC overview
  {
    label: "Introduction",
    center: [-73.97, 40.72],
    zoom: 10.5,
    bearing: 0,
    pitch: 0,
    duration: 1200,
    // Optional: highlight a specific layer when this step is active
    highlightLayer: null,
    showPopup: false,
  },
  // Step 1: The High Line
  {
    label: "The High Line",
    center: [-74.0048, 40.7480],
    zoom: 15.5,
    bearing: -29,
    pitch: 50,
    duration: 2200,
    highlightLayer: "sites-circles",
    showPopup: true,
    popupCoords: [-74.0048, 40.7480],
    popupHTML: `<div class="popup-name">The High Line</div>Chelsea, Manhattan`,
  },
  // Step 2: Times Square
  {
    label: "Times Square Plazas",
    center: [-73.9857, 40.7580],
    zoom: 16,
    bearing: 29,
    pitch: 60,
    duration: 2000,
    highlightLayer: "sites-circles",
    showPopup: true,
    popupCoords: [-73.9857, 40.7580],
    popupHTML: `<div class="popup-name">Times Square Broadway Plazas</div>Midtown Manhattan`,
  },
  // Step 3: Domino Park
  {
    label: "Domino Park",
    center: [-73.9620, 40.7150],
    zoom: 15,
    bearing: 10,
    pitch: 45,
    duration: 2200,
    showPopup: true,
    popupCoords: [-73.9442, 40.7150],
    popupHTML: `<div class="popup-name">Domino Park</div>Williamsburg, Brooklyn`,
  },
  // Step 4: Hunters Point South
  {
    label: "Hunters Point South",
    center: [-73.9590, 40.7450],
    zoom: 14,
    bearing: -15,
    pitch: 40,
    duration: 2500,
    showPopup: true,
    popupCoords: [-73.9174, 40.7614],
    popupHTML: `<div class="popup-name">Hunters Point South Park</div>Long Island City, Queens`,
  },
  // Step 5: Prospect Park
  {
    label: "Prospect Park",
    center: [-73.9693, 40.6602],
    zoom: 14,
    bearing: 0,
    pitch: 30,
    duration: 2200,
    showPopup: true,
    popupCoords: [-73.9693, 40.6602],
    popupHTML: `<div class="popup-name">Prospect Park</div>Brooklyn — est. 1867`,
  },
  // Step 6: Conclusion — pull back to overview
  {
    label: "Conclusion",
    center: [-73.97, 40.72],
    zoom: 10.5,
    bearing: 0,
    pitch: 0,
    duration: 1800,
    showPopup: false,
  },
];


/* =============================================================
   INITIALIZE THE MAP
   ============================================================= */

const map = new maplibregl.Map({
  container: "map",
  style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  center: STEPS[0].center,
  zoom: STEPS[0].zoom,
  bearing: STEPS[0].bearing,
  pitch: STEPS[0].pitch,
  interactive: true,    // keep interactive so user can pan/zoom manually between steps
});

map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");

// Track the current popup so we can close it before showing the next one
let currentPopup = null;

// Track the current active step
let currentStep = 0;


/* =============================================================
   LOAD GeoJSON DATA AFTER MAP IS READY
   ============================================================= */

map.on("load", async () => {

  try {
    const res = await fetch("./assets/data/nyc-sites.geojson");
    const data = await res.json();

    map.addSource("sites", {
      type: "geojson",
      data,
    });

    // All sites as white dots on the dark basemap
    map.addLayer({
      id: "sites-circles",
      type: "circle",
      source: "sites",
      paint: {
        "circle-radius": [
          "interpolate", ["linear"], ["zoom"],
          10, 5,
          16, 14,
        ],
        "circle-color": "white",
        "circle-opacity": 0.4,
        "circle-stroke-color": "white",
        "circle-stroke-width": 1.5,
      },
    });

    // Active site highlighted with a pulsing ring (using a separate layer)
    map.addLayer({
      id: "sites-highlight",
      type: "circle",
      source: "sites",
      filter: ["==", ["get", "id"], "__none__"],  // start hidden, filter updated on step change
      paint: {
        "circle-radius": [
          "interpolate", ["linear"], ["zoom"],
          10, 10,
          16, 24,
        ],
        "circle-color": "#3C4ED6",
        "circle-opacity": 0.9,
        "circle-stroke-color": "white",
        "circle-stroke-width": 2.5,
      },
    });

    // Labels for all sites
    map.addLayer({
      id: "sites-labels",
      type: "symbol",
      source: "sites",
      minzoom: 12,
      layout: {
        "text-field": ["get", "name"],
        "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
        "text-size": 12,
        "text-offset": [0, 1.6],
        "text-anchor": "top",
      },
      paint: {
        "text-color": "white",
        "text-halo-color": "rgba(0,0,0,0.6)",
        "text-halo-width": 2,
        "text-opacity": 0.85,
      },
    });

  } catch (err) {
    console.error("Failed to load site data:", err);
  }

  // Set up the Intersection Observer after the map is ready
  initScrollytelling();

});


/* =============================================================
   SCROLLYTELLING LOGIC
   Uses IntersectionObserver to detect which step is visible
   ============================================================= */

function initScrollytelling() {

  const stepEls = document.querySelectorAll(".step");
  const stepCounter = document.getElementById("step-counter");

  // IntersectionObserver fires when a watched element crosses the threshold.
  // threshold: 0.5 means the callback fires when 50% of the element is visible.
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const idx = parseInt(entry.target.dataset.step, 10);
          activateStep(idx, stepEls, stepCounter);
        }
      });
    },
    {
      // rootMargin lets you shift the detection zone.
      // "-30% 0px -30% 0px" means the trigger fires when the element
      // is in the middle 40% of the viewport height, which feels natural.
      rootMargin: "-30% 0px -30% 0px",
      threshold: 0,
    }
  );

  // Observe every step element
  stepEls.forEach(el => observer.observe(el));

  // Activate the first step immediately on load
  activateStep(0, stepEls, stepCounter);
}


function activateStep(idx, stepEls, stepCounter) {
  if (idx === currentStep && idx !== 0) return;  // avoid re-triggering same step
  currentStep = idx;

  const step = STEPS[idx];
  if (!step) return;

  // --- Update CSS active class ---
  stepEls.forEach(el => el.classList.remove("active"));
  stepEls[idx]?.classList.add("active");

  // --- Update step counter overlay ---
  if (stepCounter) {
    stepCounter.textContent = step.label;
  }

  // --- Fly the map ---
  map.flyTo({
    center: step.center,
    zoom: step.zoom,
    bearing: step.bearing ?? 0,
    pitch: step.pitch ?? 0,
    duration: step.duration ?? 1800,
    essential: true,
    curve: 1.4,   // how arc-like the flight path is (1 = linear, higher = more dramatic)
  });

  // --- Update highlight layer ---
  // Show the current site's dot in bright blue; dim all others
  if (map.getLayer("sites-highlight")) {
    const siteIds = [
      null,            // step 0: no highlight
      "high-line",     // step 1
      "times-square",  // step 2
      "domino-park",   // step 3
      "hunters-point", // step 4
      "prospect-park", // step 5
      null,            // step 6
    ];
    const siteId = siteIds[idx];
    if (siteId) {
      map.setFilter("sites-highlight", ["==", ["get", "id"], siteId]);
    } else {
      map.setFilter("sites-highlight", ["==", ["get", "id"], "__none__"]);
    }
  }

  // --- Show or close popup ---
  if (currentPopup) {
    currentPopup.remove();
    currentPopup = null;
  }

  if (step.showPopup && step.popupCoords) {
    // Delay popup until the flyTo animation is mostly done
    const popupDelay = step.duration ? step.duration * 0.75 : 1400;
    setTimeout(() => {
      // Only show if this step is still active (user may have scrolled past)
      if (currentStep === idx) {
        currentPopup = new maplibregl.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: 20,
        })
          .setLngLat(step.popupCoords)
          .setHTML(step.popupHTML)
          .addTo(map);
      }
    }, popupDelay);
  }
}


/* =============================================================
   NOTES FOR STUDENTS

   How to extend this:

   1. ADD MORE STEPS
      Add an object to the STEPS array and a corresponding .step
      div in scrollytelling.html with the correct data-step index.

   2. ADD VIDEO OR IMAGES inside .step-content
      Use a regular <img> tag or embed a YouTube video with an iframe.
      The panel height will expand to fit.

   3. CHANGE THE BASEMAP
      Swap the style URL in the maplibregl.Map constructor.
      CARTO Dark Matter is used here. CARTO Positron is lighter and
      better for data-heavy maps. See README for more options.

   4. ADD A PROGRESS BAR
      Track scroll position and update a CSS width property on a
      fixed <div> at the top of the page.

   5. ADD AUDIO NARRATION
      Create an <audio> element for each step and call .play() in
      the activateStep() function.

   6. ADVANCED: Animate a route line as the story progresses
      Add a GeoJSON LineString source and use map.setData() on step
      changes to progressively reveal the route geometry.
   ============================================================= */
