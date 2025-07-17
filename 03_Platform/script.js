const map = new maplibregl.Map({
    container: 'map',
    style: 'https://api.maptiler.com/maps/openstreetmap/style.json?key=UiPyE6MMkde4fIIGwHgA', // vector tile basemap
    center: [-73.936, 40.799], // East Harlem
    zoom: 13
  });
  
  map.addControl(new maplibregl.NavigationControl(), 'top-right');
  
  map.on('load', () => {
    // ---------- Google Places Points ----------
    map.addSource('google-places', {
      type: 'geojson',
      data: 'data/google_places_results.geojson'
    });
  
    map.addLayer({
      id: 'google-places-layer',
      type: 'circle',
      source: 'google-places',
      paint: {
        'circle-radius': 5,
        'circle-color': '#e83e8c'
      }
    });
  
    map.on('click', 'google-places-layer', (e) => {
      const props = e.features[0].properties;
      new maplibregl.Popup()
        .setLngLat(e.lngLat)
        .setHTML(`<strong>${props.name}</strong><br/>Type: ${props.types}`)
        .addTo(map);
    });
  
    // ---------- NTA Polygons with Choropleth ----------
    map.addSource('ntas-hvi', {
      type: 'geojson',
      data: 'data/ntas_hvi_process.geojson'
    });
  
    map.addLayer({
      id: 'ntas-hvi-fill',
      type: 'fill',
      source: 'ntas-hvi',
      paint: {
        'fill-color': [
          'interpolate',
          ['linear'],
          ['get', 'hvi-nta-2020_HVI_RANK'],
          1, '#edf8fb',
          2, '#ccece6',
          3, '#99d8c9',
          4, '#66c2a4',
          5, '#2ca25f',
          6, '#006d2c'
        ],
        'fill-opacity': 0.6
      }
    });
  
    map.addLayer({
      id: 'ntas-hvi-outline',
      type: 'line',
      source: 'ntas-hvi',
      paint: {
        'line-color': '#333',
        'line-width': 1
      }
    });
  
    map.on('click', 'ntas-hvi-fill', (e) => {
      const props = e.features[0].properties;
      new maplibregl.Popup()
        .setLngLat(e.lngLat)
        .setHTML(`<strong>${props.NTAName}</strong><br/>HVI Rank: ${props['hvi-nta-2020_HVI_RANK']}`)
        .addTo(map);
    });
  
    // ---------- Toggle Controls ----------
    document.getElementById('points-toggle').addEventListener('change', (e) => {
      map.setLayoutProperty(
        'google-places-layer',
        'visibility',
        e.target.checked ? 'visible' : 'none'
      );
    });
  
    document.getElementById('polygons-toggle').addEventListener('change', (e) => {
      const visibility = e.target.checked ? 'visible' : 'none';
      map.setLayoutProperty('ntas-hvi-fill', 'visibility', visibility);
      map.setLayoutProperty('ntas-hvi-outline', 'visibility', visibility);
    });
  });
  