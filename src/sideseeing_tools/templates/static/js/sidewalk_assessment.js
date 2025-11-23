function initSidewalkAssessmentMap() {
    const mapDiv = document.getElementById('sidewalk-assessment-map');
    if (!mapDiv) return;

    const geoPointsData = GEO_CENTERS_DATA;
    const geoPointsCoords = geoPointsData.map(point => [point.lat, point.lon]);

    let mapCenter = [-23.5505, -46.6333];
    let mapZoom = 10;
    let initialBounds = null;

    if (geoPointsCoords.length > 0) {
        initialBounds = L.latLngBounds(geoPointsCoords).pad(0.1);
        mapCenter = initialBounds.getCenter();
    }

    const overviewMap = L.map(mapDiv).setView(mapCenter, mapZoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(overviewMap);

    geoPointsData.forEach(point => {
        const latLng = [point.lat, point.lon];
        const sampleName = point.name || 'Sample';

        const marker = L.marker(latLng);
        marker.bindPopup(`<b>Sample:</b><br>${sampleName}`);

        marker.on('click', function(e) {
            const targetCenter = e.latlng;
            const targetZoom = 17;
            const currentCenter = overviewMap.getCenter();
            const currentZoom = overviewMap.getZoom();

            if (currentCenter.distanceTo(targetCenter) > 1 || currentZoom !== targetZoom) {
                overviewMap.flyTo(targetCenter, targetZoom, {
                    animate: true,
                    duration: 1.5
                });
            }
        });

        marker.addTo(overviewMap);
    });

    if (initialBounds) {
        overviewMap.fitBounds(initialBounds);
    }

    // Add centralized controls
    addFullscreenControl(overviewMap, 'sidewalk-assessment-map-container');
    addRecenterControl(overviewMap, initialBounds);

    // Make this map findable by the section switcher
    mapDiv.closest('.section-content').dataset.mapId = 'sidewalk-assessment-map';
    window.activeMaps['sidewalk-assessment-map'] = overviewMap;
}
