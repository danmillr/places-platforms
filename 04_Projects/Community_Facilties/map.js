mapboxgl.accessToken = 'pk.eyJ1IjoiZ3VvZG9uZ2RvbmciLCJhIjoiY20xZjYwN2xsMW4zeDJqcHBkbDlzam8yeCJ9.wZeYNDrxRmkwQqEnail5XQ';

const map = new mapboxgl.Map({
  container: 'map',
  style: 'mapbox://styles/guodongdong/cmd7gy0j4001m01qvfj9xa5as',
  center: [-73.935242, 40.801330],
  zoom: 13
});

let allFeatures = [];
let isochronePolygon = null;
let selectedTime = new Date();

map.on('load', () => {
  // Load and style gardens
  map.addSource('gardens', {
    type: 'geojson',
    data: 'data/Community_Gardens.geojson'
  });

  map.addLayer({
    id: 'gardens-layer',
    type: 'circle',
    source: 'gardens',
    paint: {
      'circle-radius': 6,
      'circle-color': '#4CAF50',
      'circle-stroke-width': 1,
      'circle-stroke-color': '#fff'
    }
  });

  // Load and style education
  map.addSource('education', {
    type: 'geojson',
    data: 'data/Education_Systems.geojson'
  });

  map.addLayer({
    id: 'education-layer',
    type: 'circle',
    source: 'education',
    paint: {
      'circle-radius': 5,
      'circle-color': '#FF5722',
      'circle-stroke-width': 1,
      'circle-stroke-color': '#fff'
    }
  });

  // Store combined features
  Promise.all([
    fetch('data/Community_Gardens_Structured_Hours.geojson').then(r => r.json()),
    fetch('data/Education_Systems.geojson').then(r => r.json())
  ]).then(([gardens, education]) => {
    allFeatures = gardens.features.concat(education.features);
    populateSidebar(allFeatures);
    populateTypeFilter(allFeatures);
  });
});

function populateSidebar(features) {
  const list = document.getElementById('featureList');
  list.innerHTML = '';
  features.forEach((feature, i) => {
    const li = document.createElement('li');
    li.textContent = feature.properties.name || 'Unnamed';
    li.addEventListener('click', () => drawIsochrone(feature.geometry.coordinates));
    list.appendChild(li);
  });
}

function populateTypeFilter(features) {
  const filter = document.getElementById('typeFilter');
  const types = [...new Set(features.map(f => f.properties.type).filter(Boolean))];
  types.sort().forEach(t => {
    const opt = document.createElement('option');
    opt.value = t;
    opt.textContent = t;
    filter.appendChild(opt);
  });
  filter.addEventListener('change', () => {
    const selected = filter.value;
    const filtered = selected ? allFeatures.filter(f => f.properties.type === selected) : allFeatures;
    populateSidebar(filtered);
  });
}

function drawIsochrone(coords) {
  const url = `https://api.mapbox.com/isochrone/v1/mapbox/walking/${coords[0]},${coords[1]}?contours_minutes=5&polygons=true&access_token=${mapboxgl.accessToken}`;
  fetch(url)
    .then(r => r.json())
    .then(data => {
      isochronePolygon = data;
      if (map.getSource('isochrone')) {
        map.getSource('isochrone').setData(data);
      } else {
        map.addSource('isochrone', { type: 'geojson', data });
        map.addLayer({
          id: 'isochrone-layer',
          type: 'fill',
          source: 'isochrone',
          paint: {
            'fill-color': '#0080ff',
            'fill-opacity': 0.3
          }
        });
      }
      highlightIntersectingPoints(data);
    });
}

function highlightIntersectingPoints(iso) {
  const results = allFeatures.filter(f => {
    if (!turf.booleanIntersects(f.geometry, iso.features[0].geometry)) return false;
    if (!f.properties.hours) return true; // skip filter if no schedule info

    const day = selectedTime.toLocaleString('en-US', { weekday: 'long' });
    const dayHours = f.properties.hours[day];
    if (!dayHours || !dayHours.open || !dayHours.close) return false;

    const [openH, openM] = dayHours.open.split(':').map(Number);
    const [closeH, closeM] = dayHours.close.split(':').map(Number);
    const openTime = new Date(selectedTime);
    openTime.setHours(openH, openM, 0);
    const closeTime = new Date(selectedTime);
    closeTime.setHours(closeH, closeM, 0);

    return selectedTime >= openTime && selectedTime <= closeTime;
  });

  const resultBox = document.getElementById('intersectResults');
  resultBox.innerHTML = '<strong>Open Now Within A Five Minute Walk:</strong><ul>' +
    results.map(r => `<li>${r.properties.name || 'Unnamed'}</li>`).join('') + '</ul>';
}

document.getElementById('useLocation').addEventListener('click', () => {
  if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(pos => {
      const coords = [pos.coords.longitude, pos.coords.latitude];
      drawIsochrone(coords);
      new mapboxgl.Marker().setLngLat(coords).addTo(map);
    });
  } else {
    alert('Geolocation not supported');
  }
});

document.getElementById('clearSelection').addEventListener('click', () => {
  if (map.getLayer('isochrone-layer')) map.removeLayer('isochrone-layer');
  if (map.getSource('isochrone')) map.removeSource('isochrone');
  isochronePolygon = null;
  document.getElementById('intersectResults').innerHTML = '';
});

document.getElementById('toggleGardens').addEventListener('change', (e) => {
  map.setLayoutProperty('gardens-layer', 'visibility', e.target.checked ? 'visible' : 'none');
});

document.getElementById('toggleEducation').addEventListener('change', (e) => {
  map.setLayoutProperty('education-layer', 'visibility', e.target.checked ? 'visible' : 'none');
});

document.getElementById('search').addEventListener('input', (e) => {
  const query = e.target.value.toLowerCase();
  const filtered = allFeatures.filter(f => (f.properties.name || '').toLowerCase().includes(query));
  populateSidebar(filtered);
});

// Time controls
function updateCurrentTime() {
  const now = new Date();
  document.getElementById('currentTimeDisplay').textContent =
    now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
setInterval(updateCurrentTime, 1000);

document.getElementById('customTime').addEventListener('input', (e) => {
  const timeParts = e.target.value.split(':');
  if (timeParts.length === 2) {
    const now = new Date();
    now.setHours(parseInt(timeParts[0]));
    now.setMinutes(parseInt(timeParts[1]));
    selectedTime = now;
    console.log('Selected time:', selectedTime);
  }
});
