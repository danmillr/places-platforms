# Geolocation Zones: Change the Interface Based on Where the User Is

**Status: Shell.** Structure and pattern are here; working code is not yet built.

## What you will build

A static site that asks for the visitor's location, checks whether they are inside a specific polygon (in this case, a privately owned public space), and shows a different interface depending on whether they are inside, near, or far. Inside a POPS the page might unlock hidden content; outside it might show a "get closer" prompt with a map.

## Prerequisites

- A code editor and a browser
- A GeoJSON of the POPS boundary or boundaries you want to test against. NYC POPS boundaries: https://data.cityofnewyork.us/City-Government/Privately-Owned-Public-Space-POPS/rvih-nhyn (points, so you will need to draft your own polygons or buffer them)
- Turf.js for point-in-polygon: no install, loaded via CDN

## The pattern

Three ingredients:

1. **Location** from the browser's Geolocation API.
2. **Geometry** you carry with the site (a GeoJSON in `assets/data/`).
3. **A decision function** that returns a state (`inside`, `near`, `far`) and drives the UI.

## Data sources

- NYC POPS point dataset: https://data.cityofnewyork.us/City-Government/Privately-Owned-Public-Space-POPS/rvih-nhyn
- Manhattan POPS shapefiles (research releases from advocacy groups sometimes have polygonal versions)
- For your own zones, draw polygons in geojson.io and save them locally.

## API notes

**Browser Geolocation API**

```js
navigator.geolocation.getCurrentPosition(
  pos => { const { latitude, longitude, accuracy } = pos.coords; },
  err => { /* handle denied, timeout, unavailable */ },
  { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
);
```

Notes:
- Requires HTTPS. `http://localhost` works too.
- User must grant permission each session in some browsers.
- Accuracy on desktop is often 5 to 30 km (IP-based). On mobile with GPS, 5 to 50 m.
- Use `watchPosition` to react to movement, not `getCurrentPosition`.

**Turf.js**

```html
<script src="https://cdn.jsdelivr.net/npm/@turf/turf@6.5.0/turf.min.js"></script>
```

```js
const point = turf.point([longitude, latitude]);
const inside = turf.booleanPointInPolygon(point, popsPolygon);
```

## Walkthrough (outline)

1. **Page shell** with three states: `#waiting`, `#outside`, `#inside`. All hidden except `#waiting`.
2. **Load POPS GeoJSON** on page load.
3. **Request geolocation** with a clear reason ("We need your location to check whether you are inside this public space").
4. **Decide state** using Turf. If inside any polygon, set `state = 'inside'`. If within 100 m of any polygon, `state = 'near'`. Otherwise, `state = 'far'`.
5. **Swap UI** by toggling classes on `<body>`.
6. **Watch position** and re-decide whenever the user moves more than 10 m.

## UI patterns to try

- **Inside:** unlock a comment field, show hidden imagery, reveal a poem or annotation tied to the site.
- **Near:** show a compass arrow pointing to the nearest POPS.
- **Far:** show a map with all POPS in view and their distances from the user.
- **Denied:** allow manual location entry via a search box.

## Extensions

- **Time zones.** Change the interface based on the time of day too. A POPS is legally required to be publicly accessible during specific hours; show that state.
- **Multiple polygons.** Extend to a whole city of POPS; the UI names which one the user is inside.
- **Trace a visit.** Log timestamped positions to localStorage while the user is inside, draw the trace when they leave.
- **Compass heading.** Use the DeviceOrientation API to point users toward a specific feature within the POPS.

## Common pitfalls

- **HTTPS required.** GitHub Pages serves HTTPS by default. Custom domains need a valid cert.
- **Denied permission.** Have a manual location entry fallback.
- **Accuracy on desktop.** Test on your phone. Desktop GPS is essentially useless.
- **Turf bundle size.** `turf.min.js` is ~500KB. If you only need `booleanPointInPolygon`, import that module directly.
- **Polygon direction.** GeoJSON winding order matters for some libraries. Turf handles both, but if you draw polygons by hand, keep exterior rings counterclockwise per the spec.
