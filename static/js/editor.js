// Route editor: click waypoints on the map, snap to cycling roads via OSRM,
// save as a Route. Starts blank or pre-populated when editing.
(function () {
  const ctx = window.ROUTE_CONTEXT;
  const map = L.map('map').setView([51.505, -0.09], 13);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    maxZoom: 19, subdomains: 'abcd',
    attribution: '© OpenStreetMap contributors © CARTO'
  }).addTo(map);

  const waypoints = [];          // [[lng, lat], ...]
  const waypointMarkers = [];
  let routeLine = null;
  let snappedGeometry = null;    // GeoJSON LineString
  let snappedDistance = 0;

  if (ctx.geometry && ctx.geometry.coordinates.length) {
    // When editing: show existing route, but treat endpoints as the seed
    // waypoints so the user can rebuild if they want.
    snappedGeometry = ctx.geometry;
    snappedDistance = 0; // will be overwritten on next edit
    drawSnappedLine();
    const coords = ctx.geometry.coordinates;
    addWaypoint(coords[0]);
    addWaypoint(coords[coords.length - 1]);
    if (ctx.bounds) {
      map.fitBounds([[ctx.bounds[0][1], ctx.bounds[0][0]],
                     [ctx.bounds[1][1], ctx.bounds[1][0]]]);
    }
  }

  map.on('click', e => {
    addWaypoint([e.latlng.lng, e.latlng.lat]);
    requestSnap();
  });

  document.getElementById('undo-btn').addEventListener('click', () => {
    if (!waypoints.length) return;
    waypoints.pop();
    const m = waypointMarkers.pop();
    if (m) map.removeLayer(m);
    requestSnap();
  });

  document.getElementById('clear-btn').addEventListener('click', () => {
    waypoints.length = 0;
    waypointMarkers.forEach(m => map.removeLayer(m));
    waypointMarkers.length = 0;
    if (routeLine) { map.removeLayer(routeLine); routeLine = null; }
    snappedGeometry = null;
    snappedDistance = 0;
    updateStats();
  });

  document.getElementById('save-btn').addEventListener('click', save);

  function addWaypoint(lnglat) {
    waypoints.push(lnglat);
    const marker = L.marker([lnglat[1], lnglat[0]], {draggable: true}).addTo(map);
    marker.on('dragend', () => {
      const idx = waypointMarkers.indexOf(marker);
      const p = marker.getLatLng();
      waypoints[idx] = [p.lng, p.lat];
      requestSnap();
    });
    waypointMarkers.push(marker);
    updateStats();
  }

  async function requestSnap() {
    if (waypoints.length < 2) {
      if (routeLine) { map.removeLayer(routeLine); routeLine = null; }
      snappedGeometry = null;
      snappedDistance = 0;
      updateStats();
      return;
    }
    try {
      const resp = await fetch(ctx.osrmUrl, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': ctx.csrf},
        body: JSON.stringify({waypoints}),
      });
      const data = await resp.json();
      if (!resp.ok) { setStatus('OSRM: ' + (data.error || resp.status), true); return; }
      snappedGeometry = data.geometry;
      snappedDistance = data.distance_m || 0;
      drawSnappedLine();
      setStatus('');
      updateStats();
    } catch (err) {
      setStatus('Network error contacting OSRM.', true);
    }
  }

  function drawSnappedLine() {
    if (routeLine) map.removeLayer(routeLine);
    const latlngs = snappedGeometry.coordinates.map(c => [c[1], c[0]]);
    routeLine = L.polyline(latlngs, {color: '#c0392b', weight: 4}).addTo(map);
  }

  function updateStats() {
    document.getElementById('wp-count').textContent = waypoints.length;
    const imperial = window.USER_UNITS === 'imperial';
    const value = snappedDistance * (imperial ? 0.000621371 : 0.001);
    document.getElementById('dist-display').textContent = value.toFixed(2);
    document.getElementById('dist-unit').textContent = imperial ? 'mi' : 'km';
  }

  function setStatus(msg, isError) {
    const el = document.getElementById('status');
    el.textContent = msg;
    el.className = isError ? 'err' : '';
  }

  async function save() {
    const name = document.getElementById('route-name').value.trim();
    if (!name) { setStatus('Name required.', true); return; }
    if (!snappedGeometry) { setStatus('Add at least two waypoints.', true); return; }
    const payload = {
      id: ctx.id,
      name,
      description: document.getElementById('route-desc').value,
      geometry: snappedGeometry,
      distance_m: snappedDistance,
    };
    try {
      const resp = await fetch(ctx.saveUrl, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': ctx.csrf},
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) { setStatus(data.error || 'Save failed.', true); return; }
      window.location.href = data.url;
    } catch (err) {
      setStatus('Network error saving route.', true);
    }
  }
})();
