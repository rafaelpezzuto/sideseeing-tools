function initSummaryMap() {
    const mapDiv = document.getElementById('summary-overview-map');
    if (!mapDiv) return;

    // Use ANALYSIS_FILES for corrected routes, fallback to GEO_FILES for raw routes
    const routeDataSource = (typeof ANALYSIS_FILES !== 'undefined' && Object.keys(ANALYSIS_FILES).length > 0)
        ? ANALYSIS_FILES
        : (typeof GEO_FILES !== 'undefined' ? GEO_FILES : {});

    if (Object.keys(routeDataSource).length === 0) {
        console.warn("No route data available for summary map.");
        mapDiv.innerHTML = '<div class="text-center text-gray-500">No route data to display.</div>';
        return;
    }

    let mapCenter = [-23.5505, -46.6333]; // Default center
    let mapZoom = 10;
    let initialBounds = null;

    const overviewMap = L.map(mapDiv).setView(mapCenter, mapZoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(overviewMap);

    const allPaths = [];
    const dataPromises = Object.values(routeDataSource).map(path => fetch(path).then(res => res.json()));

    Promise.all(dataPromises).then(results => {
        results.forEach(data => {
            if (data.path && data.path.length > 0) {
                allPaths.push(data.path);
            }
        });

        if (allPaths.length === 0) {
            console.warn("No valid paths found in data sources.");
            mapDiv.innerHTML = '<div class="text-center text-gray-500">No valid route paths found.</div>';
            return;
        }

        const combinedBounds = L.latLngBounds();
        const routeColor = (routeDataSource === ANALYSIS_FILES) ? '#3388ff' : '#dc3545';

        allPaths.forEach(path => {
            const polyline = L.polyline(path, { color: routeColor, weight: 5 });
            polyline.addTo(overviewMap);
            combinedBounds.extend(polyline.getBounds());
        });

        if (combinedBounds.isValid()) {
            overviewMap.fitBounds(combinedBounds, { padding: [50, 50] });
            initialBounds = combinedBounds;
        } else if (results.length > 0 && results[0].center) {
            overviewMap.setView(results[0].center, 15);
            initialBounds = overviewMap.getBounds();
        }

        addFullscreenControl(overviewMap, 'map-wrapper');
        addRecenterControl(overviewMap, initialBounds);
    });

    mapDiv.closest('.section-content').dataset.mapId = 'summary-overview-map';
    window.activeMaps['summary-overview-map'] = overviewMap;
}
