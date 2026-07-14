// assets/js/main.js
// Urban Data Explorer — Tutorial 1
// Integrations: Google Street View, Open-Meteo Weather, MTA Transit (mock)

/* =======================================================
   SECTION 1: GOOGLE STREET VIEW
   Docs: https://developers.google.com/maps/documentation/javascript/streetview
   Requires: Google Maps JS API loaded in index.html with a valid key.
   The google.maps global is available because that script loads first.
   ======================================================= */

function loadStreetView() {
  const lat = parseFloat(document.getElementById("sv-lat").value);
  const lng = parseFloat(document.getElementById("sv-lng").value);

  // Validate inputs before calling the API
  if (isNaN(lat) || isNaN(lng)) {
    alert("Please enter valid coordinates.");
    return;
  }

  const container = document.getElementById("streetview-container");

  // StreetViewPanorama takes a DOM element and an options object.
  // It renders the panorama directly into that element.
  new google.maps.StreetViewPanorama(container, {
    position: { lat, lng },
    pov: {
      heading: 34,   // compass heading in degrees (0 = north, 90 = east)
      pitch: 10,     // vertical tilt in degrees (-90 to 90)
    },
    zoom: 1,
    addressControl: false,    // hides the address box overlay
    showRoadLabels: true,
    linksControl: true,       // shows navigation arrows
    motionTrackingControl: false,
  });
}

// Run on page load so the viewer appears immediately
window.addEventListener("load", loadStreetView);


/* =======================================================
   SECTION 2: WEATHER — Open-Meteo API
   Docs: https://open-meteo.com/en/docs
   No API key required. CORS is allowed (browser requests work).
   Returns JSON with current conditions and a short forecast.
   ======================================================= */

async function loadWeather() {
  const lat = document.getElementById("wx-lat").value.trim();
  const lng = document.getElementById("wx-lng").value.trim();
  const outputEl = document.getElementById("weather-output");

  if (!lat || !lng) {
    outputEl.textContent = "Please enter coordinates.";
    return;
  }

  outputEl.innerHTML = "<em>Loading weather data&hellip;</em>";

  // Use the URL constructor to safely build query strings without string concatenation.
  const url = new URL("https://api.open-meteo.com/v1/forecast");
  url.searchParams.set("latitude", lat);
  url.searchParams.set("longitude", lng);
  url.searchParams.set("current_weather", "true");
  url.searchParams.set("hourly", "relative_humidity_2m");         // just one hourly var
  url.searchParams.set("daily", "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode");
  url.searchParams.set("temperature_unit", "fahrenheit");
  url.searchParams.set("wind_speed_unit", "mph");
  url.searchParams.set("precipitation_unit", "inch");
  url.searchParams.set("timezone", "America/New_York");
  url.searchParams.set("forecast_days", "4");

  try {
    // fetch() is the browser-native HTTP client. async/await makes the flow readable.
    const response = await fetch(url.toString());

    // A 200 status doesn't always mean valid data. Always check .ok.
    if (!response.ok) {
      throw new Error(`API returned status ${response.status}`);
    }

    // .json() parses the response body. It also returns a Promise, so we await it.
    const data = await response.json();

    renderWeather(outputEl, data);

  } catch (err) {
    // Show errors to the user and log details for debugging
    outputEl.innerHTML = `<span style="color:#d44">Error: ${err.message}</span>`;
    console.error("Weather fetch failed:", err);
  }
}

function renderWeather(el, data) {
  const cw = data.current_weather;
  const daily = data.daily;

  // Build a forecast table for the next 4 days
  const forecastRows = daily.time.map((date, i) => `
    <tr>
      <td>${formatDate(date)}</td>
      <td>${describeWMO(daily.weathercode[i])}</td>
      <td>${daily.temperature_2m_max[i]}&deg;F / ${daily.temperature_2m_min[i]}&deg;F</td>
      <td>${daily.precipitation_sum[i]}"</td>
    </tr>
  `).join("");

  el.innerHTML = `
    <div class="weather-current">
      <strong>Now:</strong>
      ${cw.temperature}&deg;F &mdash;
      ${describeWMO(cw.weathercode)} &mdash;
      Wind ${cw.windspeed} mph @ ${cw.winddirection}&deg;
    </div>
    <table class="weather-table" style="width:100%;border-collapse:collapse;margin-top:0.75rem;font-size:0.85rem;">
      <thead>
        <tr style="border-bottom:1px solid #ddd;text-align:left;">
          <th style="padding:0.3rem 0.5rem;">Date</th>
          <th>Conditions</th>
          <th>High / Low</th>
          <th>Precip</th>
        </tr>
      </thead>
      <tbody>${forecastRows}</tbody>
    </table>
    <p style="margin-top:0.5rem;font-size:0.75rem;color:#888;">
      Source: Open-Meteo.com &mdash; Updated: ${new Date().toLocaleTimeString()}
    </p>
  `;
}

// WMO weather interpretation codes
// Full reference: https://open-meteo.com/en/docs#weathervariables
function describeWMO(code) {
  const map = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm, heavy hail",
  };
  return map[code] !== undefined ? map[code] : `Code ${code}`;
}

function formatDate(dateStr) {
  // dateStr is "YYYY-MM-DD". Convert to a more readable format.
  const [y, m, d] = dateStr.split("-");
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[parseInt(m) - 1]} ${parseInt(d)}`;
}


/* =======================================================
   SECTION 3: NYC SUBWAY ARRIVALS
   Data source: MTA GTFS-Realtime
   Docs: https://api.mta.info
   API Key: free registration at https://api.mta.info/#/signup

   GTFS-RT is a binary Protocol Buffer format. Parsing it in the
   browser requires the gtfs-realtime-bindings library.
   
   For simplicity, this template uses MOCK DATA so it runs without
   a backend. To connect to the live feed, see the comments below.
   ======================================================= */

async function loadTransit() {
  const stopId = document.getElementById("stop-select").value;
  const outputEl = document.getElementById("transit-output");

  outputEl.innerHTML = "<em>Loading arrivals&hellip;</em>";

  // ---- HOW TO USE THE LIVE MTA FEED (requires a server-side proxy) ----
  //
  // The MTA GTFS-RT feeds are binary protobufs and require an API key
  // sent in a request header. Because you cannot safely expose your API key
  // in client-side code, the correct pattern is:
  //
  //   1. Set up a simple serverless function (Netlify/Vercel/Cloudflare Worker)
  //   2. The function fetches from MTA with your key in the header
  //   3. It decodes the protobuf and returns JSON to the browser
  //
  // Example MTA endpoint (subway, lines A/C/E):
  //   https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace
  // Headers required:
  //   { "x-api-key": "YOUR_MTA_API_KEY" }
  //
  // Protobuf parsing (Node.js, server side):
  //   const GtfsRealtimeBindings = require('gtfs-realtime-bindings');
  //   const feed = GtfsRealtimeBindings.transit_realtime.FeedMessage.decode(buffer);
  //
  // Filter for your stop:
  //   feed.entity.forEach(entity => {
  //     entity.tripUpdate?.stopTimeUpdate?.forEach(update => {
  //       if (update.stopId === stopId) { ... }
  //     });
  //   });
  // ---- END LIVE FEED NOTES ----

  // Using mock data in this template. Swap this function with a real API call above.
  const arrivals = getMockArrivals(stopId);
  renderArrivals(outputEl, arrivals, stopId);
}

function getMockArrivals(stopId) {
  // In a real integration, this data would come from decoding the GTFS-RT feed.
  // Each entry represents one trip stopping at the given stop.
  const now = Math.floor(Date.now() / 1000);

  const mockData = {
    "127": [
      { route: "A", destination: "Far Rockaway-Mott Av", arrivalSecs: now + 90 },
      { route: "C", destination: "Euclid Av", arrivalSecs: now + 240 },
      { route: "E", destination: "Jamaica Center", arrivalSecs: now + 420 },
      { route: "A", destination: "Lefferts Blvd", arrivalSecs: now + 700 },
    ],
    "R16": [
      { route: "N", destination: "Coney Island", arrivalSecs: now + 60 },
      { route: "Q", destination: "Stillwell Av", arrivalSecs: now + 300 },
      { route: "R", destination: "Bay Ridge-95 St", arrivalSecs: now + 540 },
    ],
    "631": [
      { route: "4", destination: "Woodlawn", arrivalSecs: now + 120 },
      { route: "5", destination: "Dyre Av", arrivalSecs: now + 360 },
      { route: "6", destination: "Pelham Bay Park", arrivalSecs: now + 480 },
    ],
    "A27": [
      { route: "A", destination: "Ozone Park", arrivalSecs: now + 200 },
      { route: "C", destination: "Rockaway Blvd", arrivalSecs: now + 450 },
    ],
  };

  return mockData[stopId] || [];
}

function renderArrivals(el, arrivals, stopId) {
  if (arrivals.length === 0) {
    el.textContent = "No arrivals found for this stop.";
    return;
  }

  const now = Math.floor(Date.now() / 1000);

  const rows = arrivals.map(a => {
    const secsAway = a.arrivalSecs - now;
    const minsAway = Math.round(secsAway / 60);
    const timeText = secsAway <= 30
      ? `<span class="arriving-now">Now</span>`
      : `${minsAway} min`;

    return `<tr>
      <td><span class="route-badge">${a.route}</span></td>
      <td>${a.destination}</td>
      <td>${timeText}</td>
    </tr>`;
  }).join("");

  el.innerHTML = `
    <p style="font-size:0.78rem;color:#888;margin-bottom:0.5rem;">
      Stop ID: <code>${stopId}</code> &mdash; Updated: ${new Date().toLocaleTimeString()}
      &mdash; <em>Mock data (see README to connect live MTA feed)</em>
    </p>
    <table class="arrivals-table">
      <thead>
        <tr>
          <th>Line</th>
          <th>Destination</th>
          <th>Arrives</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}
