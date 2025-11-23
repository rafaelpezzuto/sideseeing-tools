function initGeoSection(activeMaps, loadedGeoData) {
    const geoSelect = document.getElementById('geo-select');
    const geoMapContainer = document.getElementById('geo-map-container');
    let geoSpinner = document.getElementById('geo-map-spinner');
    let geoPlaceholder = document.getElementById('geo-map-placeholder');
    let geoMapDiv = document.getElementById('geo-map'); // Keep a reference to the original div
    let cleanupFullscreen;

    if (!geoSelect) return;

    // Make the section findable by the section switcher
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
            renderGeoMap(sampleName, loadedGeoData[jsonPath].data);
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
            .then(geoData => {
                loadedGeoData[jsonPath] = { name: sampleName, data: geoData };
                if (geoSpinner) geoSpinner.classList.add('hidden');
                renderGeoMap(sampleName, geoData);
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

        // Use a consistent key for the geo map
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
            if (geoPlaceholder) geoPlaceholder.style.display = 'block';
            if (geoSpinner) geoSpinner.classList.add('hidden');
        }
    }
    
    function renderGeoMap(sampleName, geoData) {
        const { center, path } = geoData;

        if (!path || path.length === 0) {
            alert(`No route data found for ${sampleName}.`);
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

        const polyline = L.polyline(path, { color: 'blue', opacity: 0.6, weight: 2 }).addTo(map);
        const bounds = polyline.getBounds();

        L.marker(path[0]).addTo(map).bindPopup('<b>Start</b>');
        L.marker(path[path.length - 1]).addTo(map).bindPopup('<b>End</b>');

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
