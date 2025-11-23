function initWifiSection(activeMaps, loadedWifiData) {
    const wifiSelect = document.getElementById('wifi-select');
    const wifiBandSelect = document.getElementById('wifi-band-select');
    const wifiSsidSelect = document.getElementById('wifi-ssid-select');
    const wifiMapContainer = document.getElementById('wifi-map-container');
    const wifiSpinner = document.getElementById('wifi-map-spinner');
    const wifiPlaceholder = document.getElementById('wifi-map-placeholder');
    let wifiMapDiv = document.getElementById('wifi-map'); // Keep a reference to the original div
    let cleanupFullscreen;

    if (!wifiSelect) return;

    // Make the section findable by the section switcher
    wifiMapContainer.closest('.section-content').dataset.mapId = 'wifi-map';

    wifiSelect.addEventListener('change', handleWifiSampleChange);
    wifiBandSelect.addEventListener('change', handleWifiBandChange);
    wifiSsidSelect.addEventListener('change', handleWifiSsidChange);

    function handleWifiSampleChange() {
        const selectedOption = wifiSelect.options[wifiSelect.selectedIndex];
        if (!selectedOption || !selectedOption.value) {
            resetWifiView(true);
            return;
        }

        const jsonPath = selectedOption.value;
        const sampleName = selectedOption.textContent;

        resetWifiView(false);
        wifiSpinner.classList.remove('hidden');
        wifiSpinner.classList.add('flex');
        wifiPlaceholder.style.display = 'none';

        Promise.all([
            fetch(jsonPath).then(res => res.json()),
            fetch(GEO_FILES[sampleName]).then(res => res.json())
        ]).then(([wifiData, geoData]) => {
            loadedWifiData[jsonPath] = { name: sampleName, data: wifiData, geo: geoData };
            wifiSpinner.classList.add('hidden');
            
            plotGpsPath(geoData);
            populateWifiBandSelect(jsonPath, wifiData);
        }).catch(err => {
            console.error("Error loading Wi-Fi or GPS data:", err);
            wifiSpinner.classList.add('hidden');
            wifiMapContainer.innerHTML = `<div class="col-span-full text-center p-4 text-red-600">Failed to load data.</div>`;
        });
    }

    function populateWifiBandSelect(jsonPath, wifiData) {
        const bands = new Set();
        for (const ssid in wifiData) {
            for (const band in wifiData[ssid]) {
                bands.add(band);
            }
        }

        wifiBandSelect.innerHTML = '<option selected disabled value="">-- Choose a band --</option>';
        
        if (bands.size === 0) {
            wifiBandSelect.innerHTML = '<option selected disabled value="">-- No bands found --</option>';
            wifiBandSelect.disabled = true;
            return;
        }

        [...bands].sort().forEach(band => {
            const option = document.createElement('option');
            option.value = band;
            option.textContent = band;
            option.dataset.jsonPath = jsonPath;
            wifiBandSelect.appendChild(option);
        });

        wifiBandSelect.disabled = false;
    }

    function handleWifiBandChange() {
        const selectedBandOption = wifiBandSelect.options[wifiBandSelect.selectedIndex];
        if (!selectedBandOption || !selectedBandOption.value) return;

        const band = selectedBandOption.value;
        const jsonPath = selectedBandOption.dataset.jsonPath;
        const wifiData = loadedWifiData[jsonPath].data;

        populateWifiSsidSelect(jsonPath, wifiData, band);
    }

    function populateWifiSsidSelect(jsonPath, wifiData, selectedBand) {
        const ssids = Object.keys(wifiData).filter(ssid => wifiData[ssid][selectedBand] && ssid.trim() !== '');

        wifiSsidSelect.innerHTML = '<option selected disabled value="">-- First, choose a band --</option>';
        if (ssids.length === 0) {
            wifiSsidSelect.innerHTML = '<option selected disabled value="">-- No SSIDs for this band --</option>';
            wifiSsidSelect.disabled = true;
            return;
        }

        ssids.sort().forEach(ssid => {
            const option = document.createElement('option');
            option.value = ssid;
            option.textContent = ssid;
            option.dataset.jsonPath = jsonPath;
            option.dataset.band = selectedBand;
            wifiSsidSelect.appendChild(option);
        });

        wifiSsidSelect.disabled = false;
        handleWifiSsidChange();
    }

    function handleWifiSsidChange() {
        const selectedSsidOption = wifiSsidSelect.options[wifiSsidSelect.selectedIndex];
        if (!selectedSsidOption || !selectedSsidOption.value) return;

        const ssid = selectedSsidOption.value;
        const jsonPath = selectedSsidOption.dataset.jsonPath;
        const band = selectedSsidOption.dataset.band;

        plotWifiMap(jsonPath, ssid, band);
    }

    function resetWifiView(fullReset = true) {
        if (cleanupFullscreen) {
            cleanupFullscreen();
            cleanupFullscreen = null;
        }
        const map = activeMaps['wifi-map'];
        if (map) {
            map.remove();
            delete activeMaps['wifi-map'];
        }

        if (wifiMapDiv) {
            wifiMapDiv.classList.add('hidden');
        }

        if (fullReset) {
            wifiSelect.value = '';
            wifiBandSelect.innerHTML = '<option selected disabled value="">-- First, choose a sample --</option>';
            wifiBandSelect.disabled = true;
            wifiSsidSelect.innerHTML = '<option selected disabled value="">-- First, choose a band --</option>';
            wifiSsidSelect.disabled = true;
            wifiPlaceholder.style.display = 'block';
            wifiSpinner.classList.add('hidden');
        }
    }

    function plotGpsPath(geoData) {
        const { center, path } = geoData;
        if (!path || path.length === 0) return;

        resetWifiView(false);

        wifiPlaceholder.style.display = 'none';
        wifiMapDiv.classList.remove('hidden');

        const map = L.map(wifiMapDiv).setView(center, 16);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxNativeZoom: 19,
            maxZoom: 22
        }).addTo(map);
        
        activeMaps['wifi-map'] = map;

        const gpsPath = L.polyline(path, { color: 'blue', opacity: 0.6, weight: 2 });
        const bounds = gpsPath.getBounds();

        const startMarker = L.marker(path[0]).bindPopup('<b>Start</b>');
        const endMarker = L.marker(path[path.length - 1]).bindPopup('<b>End</b>');

        const gpsPathLayer = L.layerGroup([gpsPath, startMarker, endMarker]).addTo(map);

        map.fitBounds(bounds, { padding: [20, 20] });

        cleanupFullscreen = addFullscreenControl(map, 'wifi-map-container');
        addRecenterControl(map, bounds);
        
        if (!map.signalLayers) {
            map.signalLayers = L.layerGroup().addTo(map);
        }
        map.gpsPathLayer = gpsPathLayer;
        
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    function getWifiColor(level) {
        if (level >= -50) return '#28a745'; 
        if (level >= -60) return '#a0d468';
        if (level >= -70) return '#ffd700';
        if (level >= -80) return '#ff9800';
        return '#dc3545';
    }

    function plotWifiMap(jsonPath, ssid, band) {
        const sampleData = loadedWifiData[jsonPath];
        if (!sampleData) return;

        const wifiPoints = sampleData.data[ssid][band];
        if (!wifiPoints || wifiPoints.length === 0) {
            alert(`No data found for ${ssid} (${band}).`);
            return;
        }

        const map = activeMaps['wifi-map'];
        if (!map) return;

        if (map.signalLayers) {
            map.signalLayers.clearLayers();
        } else {
            map.signalLayers = L.layerGroup().addTo(map);
        }

        wifiPoints.forEach(point => {
            const [lat, lon, level] = point;
            const color = getWifiColor(level);
            
            L.circle([lat, lon], {
                color: color,
                fillColor: color,
                fillOpacity: 0.5,
                radius: 2
            }).bindPopup(`<b>Signal:</b> ${level.toFixed(2)} dBm`).addTo(map.signalLayers);
        });

        updateLegend(map);
    }

    function updateLegend(map) {
        if (map.legend) {
            map.legend.remove();
        }
        
        const legend = L.control({position: 'bottomright'});

        legend.onAdd = function (map) {
            const div = L.DomUtil.create('div', 'info legend p-2 bg-white bg-opacity-80 rounded-md shadow text-xs');
            
            div.innerHTML = `
                <div class="font-bold mb-1">Map Layers</div>
                <div class="flex items-center">
                    <input type="checkbox" id="toggle-gps-path-wifi" class="mr-2" checked>
                    <label for="toggle-gps-path-wifi" class="flex items-center cursor-pointer">
                        <span class="w-4 h-2 mr-1" style="background:blue; opacity: 0.6;"></span> GPS Path
                    </label>
                </div>
                <div class="flex items-center">
                    <input type="checkbox" id="toggle-wifi-signal" class="mr-2" checked>
                    <label for="toggle-wifi-signal" class="cursor-pointer">WiFi Signal</label>
                </div>
                <hr class="my-2">
            `;

            const grades = [-90, -80, -70, -60, -50];
            let labels = ['<strong class="font-bold">Signal (dBm)</strong>'];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const to = grades[i + 1];
                labels.push(
                    `<div class="flex items-center"><i class="w-3 h-3 mr-2 rounded-full" style="background:${getWifiColor(from + 1)}"></i> ` +
                    `${from}` + (to ? `&ndash;${to}` : '+') + '</div>'
                );
            }
            div.innerHTML += labels.join('');

            L.DomEvent.on(div, 'click', L.DomEvent.stopPropagation);
            L.DomEvent.on(div, 'mousedown', L.DomEvent.stopPropagation);

            setTimeout(() => {
                const gpsToggle = document.getElementById('toggle-gps-path-wifi');
                const wifiToggle = document.getElementById('toggle-wifi-signal');
                
                if (gpsToggle && map.gpsPathLayer) {
                    gpsToggle.addEventListener('change', function() {
                        if (this.checked) {
                            map.addLayer(map.gpsPathLayer);
                        } else {
                            map.removeLayer(map.gpsPathLayer);
                        }
                    });
                }
                if (wifiToggle && map.signalLayers) {
                    wifiToggle.addEventListener('change', function() {
                        if (this.checked) {
                            map.addLayer(map.signalLayers);
                        } else {
                            map.removeLayer(map.signalLayers);
                        }
                    });
                }
            }, 0);

            return div;
        };

        legend.addTo(map);
        map.legend = legend;
    }
}
