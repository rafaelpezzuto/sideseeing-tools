function initGeoSection(activeMaps, loadedGeoData) {
    const geoSelect = document.getElementById('geo-select');
    const geoMapContainer = document.getElementById('geo-map-container');
    let geoSpinner = document.getElementById('geo-map-spinner');
    let geoPlaceholder = document.getElementById('geo-map-placeholder');
    let geoMapDiv = document.getElementById('geo-map');
    let cleanupFullscreen;

    if (!geoSelect) return;

    geoMapContainer.closest('.section-content').dataset.mapId = 'geo-map';

    geoSelect.addEventListener('change', handleGeoSelectionChange);

    function handleGeoSelectionChange() {
        const selectedOption = geoSelect.options[geoSelect.selectedIndex];
        if (!selectedOption || !selectedOption.value) {
            handleResetGeoView(true);
            return;
        }

        const jsonPath = selectedOption.value;
        const sampleName = selectedOption.textContent;

        handleResetGeoView(false);

        if (loadedGeoData[jsonPath]) {
            renderGeoMap(sampleName, loadedGeoData[jsonPath]);
            return;
        }

        if (geoSpinner) {
            geoSpinner.classList.remove('hidden');
            geoSpinner.classList.add('flex');
        }
        if (geoPlaceholder) geoPlaceholder.style.display = 'none';

        fetch(jsonPath)
            .then(response => {
                if (!response.ok) throw new Error(`Failed to load ${jsonPath}`);
                return response.json();
            })
            .then(data => {
                loadedGeoData[jsonPath] = data;
                if (geoSpinner) geoSpinner.classList.add('hidden');
                renderGeoMap(sampleName, data);
            })
            .catch(err => {
                console.error("Error loading GEO data:", err);
                if (geoSpinner) geoSpinner.classList.add('hidden');
                geoMapContainer.innerHTML = `<div class="p-4 text-red-600">Failed to load sample data.</div>`;
            });
    }

    function handleResetGeoView(fullReset = true) {
        if (cleanupFullscreen) {
            cleanupFullscreen();
            cleanupFullscreen = null;
        }

        const map = activeMaps['geo-map'];
        if (map) {
            map.remove();
            delete activeMaps['geo-map'];
        }

        if (geoMapDiv) {
            geoMapDiv.classList.add('hidden');
        }

        if (fullReset) {
            geoSelect.value = '';
            if (geoPlaceholder) {
                geoPlaceholder.innerHTML = `<div class="text-center text-gray-400"><i data-lucide="map-pin" class="mx-auto h-12 w-12"></i><p class="mt-2 text-lg">Select a sample to get started.</p></div>`;
                geoPlaceholder.style.display = 'block';
            }
            if (geoSpinner) geoSpinner.classList.add('hidden');
        }
    }
    
    function renderGeoMap(sampleName, data) {
        const { center, path: originalPath, corrected_path: correctedPath } = data;

        if (!originalPath || originalPath.length === 0) {
            if (geoPlaceholder) {
                geoPlaceholder.innerHTML = `<div class="text-center text-gray-400"><i data-lucide="circle-slash-2" class="mx-auto h-12 w-12"></i><p class="mt-2 text-lg">No route data found for ${sampleName}.</p></div>`;
                geoPlaceholder.style.display = 'block';
                if (window.lucide) window.lucide.createIcons();
            }
            return;
        }

        handleResetGeoView(false);

        if (geoPlaceholder) geoPlaceholder.style.display = 'none';
        if (geoMapDiv) geoMapDiv.classList.remove('hidden');

        const map = L.map(geoMapDiv).setView(center, 16);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxNativeZoom: 19,
            maxZoom: 22
        }).addTo(map);

        const bounds = L.latLngBounds();
        const overlayLayers = {};

        const originalPolyline = L.polyline(originalPath, { color: '#dc3545', opacity: 0.8, weight: 4 });
        overlayLayers["Phone GPS"] = originalPolyline;
        bounds.extend(originalPolyline.getBounds());
        originalPolyline.addTo(map);

        let startPoint, endPoint;

        if (correctedPath && correctedPath.length > 0) {
            const correctedPolyline = L.polyline(correctedPath, { color: '#3388ff', opacity: 0.8, weight: 4 });
            overlayLayers["Corrected GPS"] = correctedPolyline;
            bounds.extend(correctedPolyline.getBounds());
            correctedPolyline.addTo(map);
            startPoint = correctedPath[0];
            endPoint = correctedPath[correctedPath.length - 1];
        } else {
            startPoint = originalPath[0];
            endPoint = originalPath[originalPath.length - 1];
        }

        L.marker(startPoint).addTo(map).bindPopup('<b>Start</b>');
        L.marker(endPoint).addTo(map).bindPopup('<b>End</b>');

        // Move legend to the bottom right
        L.control.layers(null, overlayLayers, { collapsed: false, position: 'bottomright' }).addTo(map);

        map.fitBounds(bounds, { padding: [20, 20] });

        activeMaps['geo-map'] = map;
        cleanupFullscreen = addFullscreenControl(map, 'geo-map-container');
        addRecenterControl(map, bounds);

        if (window.lucide) {
            window.lucide.createIcons();
        }

        setTimeout(() => map.invalidateSize(), 10);
    }
}
