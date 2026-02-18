function initSidewalkAssessmentMap(assessmentData) {
    const mapElement = document.getElementById('sidewalk-assessment-map');
    if (!mapElement) return;

    if (!assessmentData || Object.keys(assessmentData).length === 0) {
        mapElement.innerHTML = '<div class="text-center text-gray-400"><i data-lucide="circle-slash-2" class="mx-auto h-12 w-12"></i><p class="mt-2 text-lg">No sidewalk assessment data is available for this report.</p></div>';
        return;
    }

    let map;
    let layerGroups = {};
    let cleanupFullscreen;

    let layerVisibilityState = {
        'route': true,
        'crosswalk': true,
        'curbramp': false,
        'obstacle': false,
        'surfaceproblem': false
    };

    const iconConfig = {
        'curbramp': {color: '#3498db', name: 'Curb Ramp'},
        'obstacle': {color: '#e74c3c', name: 'Obstacle'},
        'crosswalk': {color: '#2ecc71', name: 'Crosswalk'},
        'surfaceproblem': {color: '#f1c40f', name: 'Surface Problem'},
        'default': {color: '#95a5a6', name: 'Unknown'}
    };

    function createMarkerIcon(pointType) {
        const config = iconConfig[pointType] || iconConfig['default'];
        const markerHtml = `<div style="background-color: ${config.color};" class="leaflet-custom-marker"></div>`;
        return L.divIcon({
            html: markerHtml,
            className: 'leaflet-custom-icon',
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });
    }

    function addLegend() {
        const legend = L.control({position: 'bottomright'});
        legend.onAdd = function () {
            const div = L.DomUtil.create('div', 'info legend');
            div.innerHTML += '<h4>Toggle Layers</h4>';

            div.innerHTML += `
                <div class="legend-item">
                    <input type="checkbox" id="legend-checkbox-route" ${layerVisibilityState['route'] ? 'checked' : ''} class="legend-checkbox">
                    <i style="background:#3388ff; border: 2px solid #3388ff;"></i>
                    <label for="legend-checkbox-route">GPS Route</label>
                </div>`;

            for (const type in iconConfig) {
                if (type === 'default') continue;
                const config = iconConfig[type];
                const checkboxId = `legend-checkbox-${type}`;
                div.innerHTML +=
                    `<div class="legend-item">
                        <input type="checkbox" id="${checkboxId}" ${layerVisibilityState[type] ? 'checked' : ''} class="legend-checkbox">
                        <i style="background:${config.color}"></i>
                        <label for="${checkboxId}">${config.name}</label>
                    </div>`;
            }
            return div;
        };
        legend.addTo(map);

        // Bring the legend to the front
        legend.getContainer().style.zIndex = 1000;

        const routeCheckbox = document.getElementById('legend-checkbox-route');
        if (routeCheckbox) {
            routeCheckbox.addEventListener('change', (e) => {
                layerVisibilityState['route'] = e.target.checked;
                if (layerGroups['route']) {
                    if (e.target.checked) map.addLayer(layerGroups['route']);
                    else map.removeLayer(layerGroups['route']);
                }
            });
        }

        for (const type in iconConfig) {
            if (type === 'default') continue;
            const checkbox = document.getElementById(`legend-checkbox-${type}`);
            if (checkbox) {
                checkbox.addEventListener('change', (e) => {
                    layerVisibilityState[type] = e.target.checked;
                    if (layerGroups[type]) {
                        if (e.target.checked) map.addLayer(layerGroups[type]);
                        else map.removeLayer(layerGroups[type]);
                    }
                });
            }
        }
    }

    function drawPoints(points) {
        Object.keys(layerGroups).forEach(key => {
            if (key !== 'route') layerGroups[key].clearLayers();
        });
        const bounds = L.latLngBounds();

        points.forEach(point => {
            const type = point.type;
            const icon = createMarkerIcon(type);
            const marker = L.marker([point.latitude, point.longitude], {icon: icon});

            const galleryId = `gallery-${point.event_id}`;
            const initialFrame = point.frames[0] || '';
            const frameCount = point.frames.length;
            const frameText = frameCount === 1 ? 'frame' : 'frames';

            const popupContent = `
                <div class="flex justify-between items-center">
                    <div class="font-semibold text-gray-700 capitalize">${iconConfig[type] ? iconConfig[type].name : 'Unknown'}</div>
                    <a href="${initialFrame}" target="_blank" title="Open image in new tab" class="text-gray-400 hover:text-blue-500 external-link">
                        <i data-lucide="external-link" class="w-4 h-4"></i>
                    </a>
                </div>
                <div id="${galleryId}" class="relative">
                    <a href="${initialFrame}" target="_blank" class="image-link">
                        <img src="${initialFrame}" alt="Frame for ${type}" class="mt-2 rounded gallery-image">
                    </a>
                    ${frameCount > 1 ? `
                    <div class="absolute inset-0 flex items-center justify-between">
                        <button class="gallery-prev bg-gray-800 bg-opacity-50 text-white p-1 rounded-full hover:bg-opacity-75 focus:outline-none">
                            <i data-lucide="chevron-left" class="w-6 h-6"></i>
                        </button>
                        <button class="gallery-next bg-gray-800 bg-opacity-50 text-white p-1 rounded-full hover:bg-opacity-75 focus:outline-none">
                            <i data-lucide="chevron-right" class="w-6 h-6"></i>
                        </button>
                    </div>
                    <div class="absolute bottom-2 right-2 bg-gray-800 bg-opacity-75 text-white text-xs px-2 py-1 rounded">
                        <span class="gallery-counter">1</span> / ${frameCount}
                    </div>
                    ` : ''}
                </div>
                <div class="text-xs text-gray-500 mt-1">Duration: ${point.length_meters.toFixed(2)}m (${frameCount} ${frameText})</div>
            `;
            marker.bindPopup(popupContent, {minWidth: 400});

            marker.on('popupopen', function (e) {
                const popup = e.popup;
                const gallery = popup.getElement().querySelector(`#${galleryId}`);
                if (!gallery) return;

                let currentIndex = 0;
                const frames = point.frames;
                const image = gallery.querySelector('.gallery-image');
                const counter = gallery.querySelector('.gallery-counter');
                const prevButton = gallery.querySelector('.gallery-prev');
                const nextButton = gallery.querySelector('.gallery-next');
                const imageLink = gallery.querySelector('.image-link');
                const externalLink = popup.getElement().querySelector('.external-link');

                function updateGallery() {
                    const framePath = frames[currentIndex];
                    image.src = framePath;
                    imageLink.href = framePath;
                    externalLink.href = framePath;
                    if (counter) counter.textContent = currentIndex + 1;
                }

                if (prevButton) {
                    prevButton.addEventListener('click', () => {
                        currentIndex = (currentIndex - 1 + frames.length) % frames.length;
                        updateGallery();
                    });
                }

                if (nextButton) {
                    nextButton.addEventListener('click', () => {
                        currentIndex = (currentIndex + 1) % frames.length;
                        updateGallery();
                    });
                }
                
                if (window.lucide) {
                    window.lucide.createIcons({
                        nodes: [
                            popup.getElement().querySelector('[data-lucide="external-link"]'),
                            ...(gallery.querySelectorAll('[data-lucide="chevron-left"], [data-lucide="chevron-right"]'))
                        ]
                    });
                }
            });

            if (layerGroups[type]) {
                layerGroups[type].addLayer(marker);
            }
            bounds.extend([point.latitude, point.longitude]);
        });

        return bounds;
    }

    function drawRoute(path) {
        if (layerGroups['route']) {
            layerGroups['route'].clearLayers();
        }
        if (path && path.length > 0) {
            const polyline = L.polyline(path, {color: '#3388ff', weight: 5});
            layerGroups['route'].addLayer(polyline);
            return polyline.getBounds();
        }
        return null;
    }

    function setupMap(center, zoom) {
        if (map) {
            map.remove();
            delete window.activeMaps[mapElement.id];
        }

        map = L.map(mapElement, {maxZoom: 20}).setView(center, zoom);
        window.activeMaps[mapElement.id] = map;

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 21,
            maxNativeZoom: 19
        }).addTo(map);

        layerGroups = {'route': L.layerGroup()};
        Object.keys(iconConfig).forEach(type => {
            if (type !== 'default') {
                layerGroups[type] = L.layerGroup();
            }
        });

        for (const layerName in layerGroups) {
            if (layerVisibilityState[layerName]) {
                layerGroups[layerName].addTo(map);
            }
        }

        addLegend();
        cleanupFullscreen = addFullscreenControl(map, 'sidewalk-assessment-map-wrapper');
    }

    function loadAllSamples() {
        const allPoints = [];
        const allPaths = [];
        const dataPromises = Object.values(assessmentData).map(path => fetch(path).then(res => res.json()));

        Promise.all(dataPromises).then(results => {
            results.forEach(data => {
                if (data.points) allPoints.push(...data.points);
                if (data.path && data.path.length > 0) allPaths.push(data.path);
            });

            const center = results.length > 0 && results[0].center ? results[0].center : [0, 0];
            setupMap(center, 13);

            const pointsBounds = drawPoints(allPoints);
            const combinedBounds = L.latLngBounds();
            if (pointsBounds.isValid()) combinedBounds.extend(pointsBounds);

            allPaths.forEach(path => {
                const polyline = L.polyline(path, {color: '#3388ff', weight: 5});
                layerGroups['route'].addLayer(polyline);
                combinedBounds.extend(polyline.getBounds());
            });

            if (combinedBounds.isValid()) {
                map.fitBounds(combinedBounds, {padding: [50, 50]});
                addRecenterControl(map, combinedBounds);
            }
            if (window.lucide) window.lucide.createIcons();
        });
    }

    function loadSingleSample(sampleName) {
        const dataPath = assessmentData[sampleName];
        if (!dataPath) return;

        fetch(dataPath)
            .then(response => response.json())
            .then(data => {
                setupMap(data.center || [0, 0], 16);

                const pointsBounds = drawPoints(data.points || []);
                const routeBounds = drawRoute(data.path || []);

                const combinedBounds = L.latLngBounds();
                if (pointsBounds.isValid()) combinedBounds.extend(pointsBounds);
                if (routeBounds && routeBounds.isValid()) combinedBounds.extend(routeBounds);

                if (combinedBounds.isValid()) {
                    map.fitBounds(combinedBounds, {padding: [50, 50]});
                    addRecenterControl(map, combinedBounds);
                }
                if (window.lucide) window.lucide.createIcons();
            });
    }

    const sampleSelector = document.getElementById('sidewalk-assessment-sample-selector');
    if (sampleSelector) {
        const sampleNames = Object.keys(assessmentData);

        const allSamplesOption = document.createElement('option');
        allSamplesOption.value = 'all';
        allSamplesOption.textContent = 'Show All Samples';
        sampleSelector.appendChild(allSamplesOption);

        const divider = document.createElement('option');
        divider.disabled = true;
        divider.textContent = '──────────';
        sampleSelector.appendChild(divider);

        sampleNames.forEach(sampleName => {
            const option = document.createElement('option');
            option.value = sampleName;
            option.textContent = sampleName;
            sampleSelector.appendChild(option);
        });

        if (sampleNames.length > 0) {
            const firstSample = sampleNames[0];
            sampleSelector.value = firstSample;
            loadSingleSample(firstSample);
        } else {
            sampleSelector.value = 'all';
            loadAllSamples();
        }

        sampleSelector.addEventListener('change', (event) => {
            if (event.target.value === 'all') {
                loadAllSamples();
            } else {
                loadSingleSample(event.target.value);
            }
        });
    }
}
