/**
 * Adds a fullscreen toggle control to a Leaflet map.
 * @param {L.Map} mapInstance - The Leaflet map instance.
 * @param {string} wrapperId - The ID of the HTML element that wraps the map container.
 * @returns {function} A cleanup function to remove the event listener and the control.
 */
function addFullscreenControl(mapInstance, wrapperId) {
    const mapWrapper = document.getElementById(wrapperId);
    if (!mapWrapper) {
        console.error(`Fullscreen wrapper element with ID '${wrapperId}' not found.`);
        return () => {}; // Return a no-op cleanup function
    }

    let fullscreenControl;

    const FullscreenControl = L.Control.extend({
        options: {
            position: 'topright'
        },
        onAdd: function() {
            const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
            container.title = "Toggle Fullscreen";
            container.innerHTML = '<i data-lucide="maximize" class="text-gray-600"></i>';

            L.DomEvent.disableClickPropagation(container);
            L.DomEvent.on(container, 'click', () => {
                if (!document.fullscreenElement) {
                    mapWrapper.requestFullscreen().catch(err => {
                        alert(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
                    });
                } else {
                    if (document.exitFullscreen) {
                        document.exitFullscreen();
                    }
                }
            });
            return container;
        }
    });

    fullscreenControl = new FullscreenControl();
    fullscreenControl.addTo(mapInstance);

    const updateFullscreenState = () => {
        if (!mapWrapper || !fullscreenControl) return;

        const controlContainer = fullscreenControl.getContainer();
        if (!controlContainer) return;

        const icon = controlContainer.querySelector('i');
        const isFullscreen = document.fullscreenElement === mapWrapper;

        mapWrapper.classList.toggle('is-fullscreen', isFullscreen);

        if (icon) {
            icon.setAttribute('data-lucide', isFullscreen ? 'minimize' : 'maximize');
        }

        if (window.lucide) {
            window.lucide.createIcons();
        }

        setTimeout(() => {
            mapInstance.invalidateSize();
            // Recenter the map after fullscreen change
            if (mapInstance.recenter) {
                mapInstance.recenter();
            }
        }, 100);
    };

    document.addEventListener('fullscreenchange', updateFullscreenState);

    // Return a cleanup function
    return () => {
        document.removeEventListener('fullscreenchange', updateFullscreenState);
        if (mapInstance && fullscreenControl) {
            mapInstance.removeControl(fullscreenControl);
        }
    };
}

/**
 * Adds a recenter control to a Leaflet map.
 * @param {L.Map} mapInstance - The Leaflet map instance.
 * @param {L.LatLngBounds} initialBounds - The initial bounds to recenter to.
 */
function addRecenterControl(mapInstance, initialBounds) {
    const RecenterControl = L.Control.extend({
        options: {
            position: 'topright' 
        },
        onAdd: function(map) {
            const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
            
            container.innerHTML = '&#x27f3;'; // Unicode for a refresh-like arrow
            container.title = "Recenter Map";
            
            container.style.backgroundColor = 'white';
            container.style.width = '30px';
            container.style.height = '30px';
            container.style.textAlign = 'center';
            container.style.lineHeight = '30px';
            container.style.fontSize = '1.6rem';
            container.style.fontWeight = 'bold';
            container.style.cursor = 'pointer';

            L.DomEvent.disableClickPropagation(container);

            L.DomEvent.on(container, 'click', () => {
                if (mapInstance.recenter) {
                    mapInstance.recenter();
                }
            });

            return container;
        }
    });

    // Attach the recenter method to the map instance
    mapInstance.recenter = () => {
        if (initialBounds && initialBounds.isValid()) {
            mapInstance.flyToBounds(initialBounds, { padding: [20, 20] });
        }
    };

    new RecenterControl().addTo(mapInstance);
}