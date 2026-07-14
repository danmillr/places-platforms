# Tutorial 1: Building and Hosting a Static Website with GitHub Pages

This tutorial walks you through creating a static website with HTML, CSS, and JavaScript, then hosting it for free on GitHub Pages. You'll also learn how to integrate real-world data APIs: Google Street View, weather data, and transit feeds.

---

## What You'll Build

A single-page site that:
- Has clean, responsive layout (HTML + CSS)
- Shows an embedded Street View panorama for a location
- Pulls live weather data from the Open-Meteo API
- Displays real-time NYC subway arrivals from the MTA feed

---

## Part 1: File and Folder Structure

A well-organized static site looks like this:

```
my-site/
├── index.html          ← your main page
├── assets/
│   ├── css/
│   │   └── style.css   ← all styles
│   └── js/
│       └── main.js     ← all JavaScript
└── img/                ← local images (optional)
```

Keep this structure from the start. GitHub Pages serves `index.html` automatically, so that file is always your entry point.

---

## Part 2: Setting Up GitHub Pages

### Step 1: Create a repository

1. Go to [github.com](https://github.com) and click **New repository**
2. Name it `my-site` (or anything you like)
3. Set it to **Public** (required for free GitHub Pages)
4. Check **Add a README file**
5. Click **Create repository**

### Step 2: Upload your files

Option A (browser, easiest to start):
- Click **Add file → Upload files**
- Drag your `index.html`, `assets/` folder, etc.
- Click **Commit changes**

Option B (Git, recommended for ongoing work):
```bash
git clone https://github.com/YOUR-USERNAME/my-site.git
cd my-site
# add your files here
git add .
git commit -m "initial site"
git push
```

### Step 3: Enable GitHub Pages

1. Go to your repo's **Settings** tab
2. Click **Pages** in the left sidebar
3. Under **Source**, choose **Deploy from a branch**
4. Select **main** branch, **/ (root)** folder
5. Click **Save**

Your site will be live at `https://YOUR-USERNAME.github.io/my-site/` within 1-2 minutes. Every time you push a commit, GitHub rebuilds the site automatically.

> **Tip:** If you name your repository `YOUR-USERNAME.github.io` (exactly), the site will be served at your root domain without the `/my-site/` path.

---

## Part 3: HTML Template

This is your `index.html` starting point. It links your CSS and JS and has semantic structure with three demo sections.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>My Site</title>
  <link rel="stylesheet" href="assets/css/style.css" />
</head>
<body>

  <header>
    <h1>Urban Data Explorer</h1>
    <p class="subtitle">Live APIs + Street View + Transit</p>
  </header>

  <main>

    <!-- SECTION 1: Street View -->
    <section id="streetview-section" class="card">
      <h2>Street View</h2>
      <p>Enter coordinates to explore a location.</p>
      <div class="input-row">
        <input id="sv-lat" type="number" step="any" placeholder="Latitude" value="40.7580" />
        <input id="sv-lng" type="number" step="any" placeholder="Longitude" value="-73.9855" />
        <button onclick="loadStreetView()">Load</button>
      </div>
      <div id="streetview-container"></div>
    </section>

    <!-- SECTION 2: Weather -->
    <section id="weather-section" class="card">
      <h2>Current Weather</h2>
      <div class="input-row">
        <input id="wx-lat" type="number" step="any" placeholder="Latitude" value="40.7128" />
        <input id="wx-lng" type="number" step="any" placeholder="Longitude" value="-74.0060" />
        <button onclick="loadWeather()">Get Weather</button>
      </div>
      <div id="weather-output" class="output-box">Press the button to load weather data.</div>
    </section>

    <!-- SECTION 3: Transit -->
    <section id="transit-section" class="card">
      <h2>NYC Subway Arrivals</h2>
      <p>Arrivals at a selected stop, via the MTA GTFS-RT feed.</p>
      <div class="input-row">
        <select id="stop-select">
          <option value="127">Times Sq-42 St (A/C/E)</option>
          <option value="R16">Times Sq-42 St (N/Q/R/W)</option>
          <option value="631">Grand Central-42 St (4/5/6)</option>
          <option value="A27">Fulton St (A/C)</option>
        </select>
        <button onclick="loadTransit()">Load Arrivals</button>
      </div>
      <div id="transit-output" class="output-box">Select a stop and click Load Arrivals.</div>
    </section>

  </main>

  <footer>
    <p>Built for Urban Planning Studio | Data from Open-Meteo, Google Maps, MTA</p>
  </footer>

  <!-- Load Google Maps JS API (replace YOUR_KEY) -->
  <script src="https://maps.googleapis.com/maps/api/js?key=YOUR_GOOGLE_MAPS_KEY"></script>
  <!-- Your JS file, loaded last so the DOM is ready -->
  <script src="assets/js/main.js"></script>

</body>
</html>
```

**Key things to notice:**
- `<script>` tags go at the **bottom** of `<body>` so they don't block page rendering
- The Google Maps API script tag must come before `main.js` because `main.js` depends on it
- Replace `YOUR_GOOGLE_MAPS_KEY` with your actual key (see API notes below)

---

## Part 4: CSS Template

```css
/* assets/css/style.css */

/* ---- Reset and base ---- */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: "Inter", system-ui, sans-serif;
  background: #f5f5f5;
  color: #1a1a1a;
  line-height: 1.6;
}

/* ---- Header ---- */
header {
  background: #1B1B33;
  color: white;
  padding: 2rem;
  text-align: center;
}

header h1 {
  font-size: 2rem;
  font-weight: 700;
}

.subtitle {
  color: #a0a0c0;
  margin-top: 0.5rem;
}

/* ---- Layout ---- */
main {
  max-width: 860px;
  margin: 2rem auto;
  padding: 0 1rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* ---- Cards ---- */
.card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.card h2 {
  font-size: 1.25rem;
  margin-bottom: 0.75rem;
  border-bottom: 2px solid #3C4ED6;
  padding-bottom: 0.5rem;
}

/* ---- Inputs ---- */
.input-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin: 1rem 0;
}

input[type="number"],
select {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 0.4rem 0.6rem;
  font-size: 0.9rem;
  flex: 1;
  min-width: 120px;
}

button {
  background: #3C4ED6;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.4rem 1rem;
  cursor: pointer;
  font-size: 0.9rem;
  white-space: nowrap;
}

button:hover {
  background: #2f3fb5;
}

/* ---- Output boxes ---- */
.output-box {
  background: #f8f8fc;
  border: 1px solid #e0e0ef;
  border-radius: 4px;
  padding: 1rem;
  font-size: 0.9rem;
  min-height: 80px;
}

/* ---- Street View container ---- */
#streetview-container {
  width: 100%;
  height: 400px;
  border-radius: 4px;
  overflow: hidden;
  background: #eee;
}

/* ---- Footer ---- */
footer {
  text-align: center;
  padding: 2rem;
  color: #666;
  font-size: 0.85rem;
}

/* ---- Responsive ---- */
@media (max-width: 600px) {
  header h1 { font-size: 1.4rem; }
  .input-row { flex-direction: column; }
}
```

---

## Part 5: JavaScript — API Integrations

This is the complete `main.js` file with all three integrations explained with inline comments.

```javascript
// assets/js/main.js

/* ==============================================
   SECTION 1: GOOGLE STREET VIEW EMBED
   API Docs: https://developers.google.com/maps/documentation/javascript/streetview
   Requires: Google Maps JS API key (free tier has generous quota)
   ============================================== */

function loadStreetView() {
  const lat = parseFloat(document.getElementById("sv-lat").value);
  const lng = parseFloat(document.getElementById("sv-lng").value);
  const container = document.getElementById("streetview-container");

  // The StreetViewPanorama class renders directly into a DOM element.
  // google.maps is available because we loaded the Maps JS API script in index.html.
  new google.maps.StreetViewPanorama(container, {
    position: { lat, lng },
    pov: { heading: 34, pitch: 10 },  // heading = compass bearing, pitch = up/down tilt
    zoom: 1,
    addressControl: false,            // hide the address overlay for a cleaner look
    linksControl: true,               // allow navigation arrows
  });
}

// Load a default view when the page opens
window.addEventListener("load", loadStreetView);


/* ==============================================
   SECTION 2: WEATHER DATA (Open-Meteo API)
   API Docs: https://open-meteo.com/en/docs
   No API key required. Completely free.
   Returns hourly or current weather for any lat/lng.
   ============================================== */

async function loadWeather() {
  const lat = document.getElementById("wx-lat").value;
  const lng = document.getElementById("wx-lng").value;
  const outputEl = document.getElementById("weather-output");

  outputEl.textContent = "Loading...";

  // Build the API URL. We request current_weather plus some daily values.
  // See https://open-meteo.com/en/docs for all available variables.
  const url = new URL("https://api.open-meteo.com/v1/forecast");
  url.searchParams.set("latitude", lat);
  url.searchParams.set("longitude", lng);
  url.searchParams.set("current_weather", true);
  url.searchParams.set("daily", "temperature_2m_max,temperature_2m_min,precipitation_sum");
  url.searchParams.set("temperature_unit", "fahrenheit");
  url.searchParams.set("wind_speed_unit", "mph");
  url.searchParams.set("timezone", "America/New_York");
  url.searchParams.set("forecast_days", 3);  // only need a short window

  try {
    // fetch() is the modern way to make HTTP requests from the browser.
    // It returns a Promise, so we use async/await.
    const response = await fetch(url);

    // Always check if the request succeeded before trying to parse JSON.
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    const cw = data.current_weather;

    // Format and display the result
    const html = `
      <strong>Current Conditions</strong><br/>
      Temperature: ${cw.temperature}°F<br/>
      Wind Speed: ${cw.windspeed} mph<br/>
      Wind Direction: ${cw.winddirection}°<br/>
      Weather Code: ${describeWMO(cw.weathercode)}<br/>
      <br/>
      <strong>3-Day Forecast</strong><br/>
      ${data.daily.time.map((date, i) => `
        ${date}: High ${data.daily.temperature_2m_max[i]}°F /
        Low ${data.daily.temperature_2m_min[i]}°F,
        Precip: ${data.daily.precipitation_sum[i]}"`
      ).join("<br/>")}
    `;
    outputEl.innerHTML = html;

  } catch (err) {
    outputEl.textContent = `Error: ${err.message}`;
    console.error(err);
  }
}

// WMO weather code descriptions (abbreviated)
// Full list: https://open-meteo.com/en/docs#weathervariables
function describeWMO(code) {
  const codes = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Heavy showers",
    95: "Thunderstorm", 99: "Thunderstorm with hail",
  };
  return codes[code] || `Code ${code}`;
}


/* ==============================================
   SECTION 3: NYC SUBWAY ARRIVALS (MTA GTFS-RT)
   API Docs: https://api.mta.info/
   Requires: free MTA API key from https://api.mta.info/#/signup
   GTFS-RT is a binary protobuf format. The MTA also exposes a
   JSON proxy at bustime.mta.info for simpler access.
   
   NOTE: Browser-side GTFS-RT parsing requires the gtfs-realtime-bindings
   library. For a simpler no-library approach, we use an unofficial
   JSON proxy here. For production, process the feed server-side.
   ============================================== */

async function loadTransit() {
  const stopId = document.getElementById("stop-select").value;
  const outputEl = document.getElementById("transit-output");
  outputEl.textContent = "Loading...";

  // This endpoint is a community-maintained JSON wrapper around MTA's GTFS-RT feeds.
  // Replace with your own server-side proxy in production to embed your API key securely.
  // See: https://github.com/jonthornton/GTFS-Realtime-Bindings for proper GTFS-RT parsing
  const url = `https://collector-otp-prod.camsys-apps.com/realtime/gtfsrt/filtered/alerts?type=json&agency=MTASBWY`;

  // Pattern for a real MTA GTFS-RT request (do this server-side):
  //
  //   const mtaUrl = `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace`;
  //   const response = await fetch(mtaUrl, {
  //     headers: { "x-api-key": "YOUR_MTA_API_KEY" }
  //   });
  //   // Then decode the protobuf response using gtfs-realtime-bindings

  // Simulated mock response for tutorial purposes (swap this for a live feed):
  const arrivals = getMockArrivals(stopId);
  renderArrivals(outputEl, arrivals, stopId);
}

function getMockArrivals(stopId) {
  // In a real implementation, parse your GTFS-RT feed here.
  // This mock simulates what you'd extract from the decoded protobuf.
  const base = Math.floor(Date.now() / 1000);
  return [
    { route: "A", destination: "Far Rockaway", arrivalSecs: base + 120 },
    { route: "C", destination: "Euclid Av", arrivalSecs: base + 300 },
    { route: "E", destination: "Jamaica Center", arrivalSecs: base + 480 },
    { route: "A", destination: "Lefferts Blvd", arrivalSecs: base + 600 },
  ];
}

function renderArrivals(el, arrivals, stopId) {
  const now = Math.floor(Date.now() / 1000);
  const rows = arrivals.map(a => {
    const minsAway = Math.round((a.arrivalSecs - now) / 60);
    return `<tr>
      <td><span class="route-badge">${a.route}</span></td>
      <td>${a.destination}</td>
      <td>${minsAway <= 0 ? "Arriving" : `${minsAway} min`}</td>
    </tr>`;
  }).join("");

  el.innerHTML = `
    <p style="margin-bottom:0.5rem;font-size:0.8rem;color:#666;">
      Stop ID: ${stopId} | Updated: ${new Date().toLocaleTimeString()}
    </p>
    <table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
      <thead>
        <tr style="text-align:left;border-bottom:1px solid #ddd;">
          <th>Line</th><th>To</th><th>Arrives</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}
```

Add this CSS for the route badge inside `style.css`:

```css
.route-badge {
  display: inline-block;
  background: #3C4ED6;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  text-align: center;
  line-height: 24px;
  font-size: 0.8rem;
  font-weight: bold;
}
```

---

## Part 6: API Keys and Security

| API | Key Required? | Cost | Notes |
|-----|--------------|------|-------|
| Open-Meteo | No | Free | No setup needed |
| Google Maps (Street View) | Yes | Free tier: $200/mo credit | Restrict key to your domain |
| MTA GTFS-RT | Yes | Free | Sign up at api.mta.info |

**Important: never commit API keys to public GitHub repos.** For a static site:

1. For Google Maps, restrict your key in the [Google Cloud Console](https://console.cloud.google.com) to only your GitHub Pages domain (`https://YOUR-USERNAME.github.io/*`). That way, even if someone sees the key in your HTML, they can't use it elsewhere.
2. For MTA keys and anything more sensitive, you need a small backend (a serverless function on Netlify, Vercel, or Cloudflare Pages) to proxy requests. This is beyond the scope of a purely static site, but it's the right pattern at scale.

---

## Part 7: Deploying Updates

Every time you push to your `main` branch, GitHub Pages rebuilds automatically:

```bash
git add .
git commit -m "update: added weather section"
git push
```

To check build status, go to your repo's **Actions** tab. You'll see a "pages build and deployment" workflow.

---

## Common Pitfalls

- **Paths are case-sensitive on GitHub Pages** (even if they work locally on Mac/Windows). Use lowercase for all filenames and folder names.
- **No server-side code.** PHP, Python, Node.js, etc. don't run on GitHub Pages. Everything must be client-side JS or calls to external APIs.
- **CORS.** Some APIs block browser-side requests. If you see a `CORS` error in the console, the API requires a server-side proxy. Open-Meteo explicitly allows browser requests. MTA's raw GTFS-RT feed does not.
- **Caching.** GitHub Pages aggressively caches. If your changes aren't showing, try hard-refreshing (`Ctrl+Shift+R`) or wait a few minutes.

---

## Resources

- [GitHub Pages Docs](https://docs.github.com/en/pages)
- [Open-Meteo API Docs](https://open-meteo.com/en/docs)
- [Google Maps JS API: Street View](https://developers.google.com/maps/documentation/javascript/streetview)
- [MTA Developer Resources](https://api.mta.info/)
- [MDN: Using Fetch](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)
