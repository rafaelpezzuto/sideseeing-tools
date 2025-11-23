document.addEventListener('DOMContentLoaded', () => {
    let activeMaps = {};
    window.activeMaps = activeMaps; // Make it globally accessible for other scripts
    let loadedSamplesData = {};
    let loadedWifiData = {};
    let loadedGeoData = {};

    lucide.createIcons();
    initSummaryMap();
    initSidewalkAssessmentMap();
    renderTable(SAMPLES_DATA);
    showSection('summary');
    
    initSensorSection(loadedSamplesData);
    initWifiSection(activeMaps, loadedWifiData);
    initGeoSection(activeMaps, loadedGeoData);
    initializeSimpleSection('video');
    initializeSimpleSection('cell');

    // --- Sidebar and Menu Logic ---
    document.getElementById('sidebar-open-btn').addEventListener('click', toggleSidebar);
    document.getElementById('sidebar-close-btn').addEventListener('click', toggleSidebar);
    document.getElementById('mobile-overlay').addEventListener('click', toggleSidebar);

    document.querySelectorAll('.menu-toggle').forEach(button => {
        const targetId = button.dataset.target;
        const target = document.getElementById(targetId);
        const icon = button.querySelector('.menu-toggle-icon');
        const storageKey = `menu-state-${targetId}`;
        const isExpanded = (localStorage.getItem(storageKey) === 'expanded') || (localStorage.getItem(storageKey) === null && targetId !== 'submenu-resources');

        target.style.maxHeight = isExpanded ? target.scrollHeight + "px" : "0px";
        if (isExpanded) icon.style.transform = 'rotate(180deg)';

        button.addEventListener('click', () => {
            const isCurrentlyExpanded = target.style.maxHeight !== "0px";
            target.style.maxHeight = isCurrentlyExpanded ? "0px" : target.scrollHeight + "px";
            icon.style.transform = isCurrentlyExpanded ? 'rotate(0deg)' : 'rotate(180deg)';
            localStorage.setItem(storageKey, isCurrentlyExpanded ? 'collapsed' : 'expanded');
        });
    });

    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const sectionId = link.getAttribute('data-section');
            showSection(sectionId);
        });
    });

    function showSection(sectionId) {
        const sectionElementId = `${sectionId}-section`;
        const activeSection = document.getElementById(sectionElementId);
        if (!activeSection) {
            console.warn(`Section ${sectionElementId} not found.`);
            return;
        }

        document.querySelectorAll('.section-content').forEach(section => {
            section.classList.remove('active');
        });
        activeSection.classList.add('active');

        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('bg-blue-600', 'text-white', 'shadow-lg', 'shadow-blue-900/50');
            link.classList.add('text-slate-400', 'hover:bg-slate-800');
        });

        const activeLink = document.querySelector(`.nav-link[data-section="${sectionId}"]`);
        if (activeLink) {
            activeLink.classList.add('bg-blue-600', 'text-white', 'shadow-lg', 'shadow-blue-900/50');
            activeLink.classList.remove('text-slate-400');
            activeLink.classList.remove('hover:bg-slate-800');
        }

        setTimeout(() => {
            // Invalidate Plotly charts
            const plotlyCharts = activeSection.querySelectorAll('.plotly-chart');
            plotlyCharts.forEach(chartDiv => {
                if (chartDiv.data) {
                    Plotly.Plots.resize(chartDiv);
                }
            });

            // Invalidate and recenter Leaflet maps
            const mapId = activeSection.dataset.mapId;
            if (mapId && activeMaps[mapId]) {
                const map = activeMaps[mapId];
                map.invalidateSize();
                if (map.recenter) {
                    map.recenter();
                }
            }
        }, 150);
    }

    function formatNumber(value) {
        const num = Number(value);
        if (isNaN(num)) {
            return value;
        }
        return num.toLocaleString('en-US');
    }

    function renderTable(data) {
        const tbody = document.getElementById('tableBody');
        tbody.innerHTML = '';

        if (data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="10" class="p-8 text-center text-gray-400">No samples found.</td></tr>`;
            document.getElementById('resultCount').textContent = '0 results';
            return;
        }
    
        data.forEach((sample, index) => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-slate-50 transition-colors group text-sm';
    
            row.innerHTML = `
                <td class="px-4 py-3 font-medium text-slate-600">${index + 1}</td>
                <td class="px-4 py-3">
                    <div class="font-semibold text-slate-600">${sample.name}</div>
                    <div class="text-xs text-slate-500">${sample.location}</div>
                </td>
                <td class="px-4 py-3 text-right text-slate-600">${formatNumber(sample.distance_km)}</td>
                <td class="px-4 py-3 text-right text-slate-600">${formatNumber(sample.duration)}</td>
                <td class="px-4 py-3">
                    <div class="text-slate-600 text-right">${formatNumber(sample.video_frames)}</div>
                    <div class="text-xs text-slate-500 text-right">@${sample.video_fps}</div>
                </td>
                <td class="px-4 py-3 text-center text-slate-600">${sample.video_resolution}</td>
                <td class="px-4 py-3">
                    <div class="text-slate-600 text-center">${sample.collection_date}</div>
                    <div class="text-xs text-slate-500 text-center">${sample.collection_datetime}</div>
                </td>
                <td class="px-4 py-3 text-center text-slate-600">${formatNumber(sample.sensors)}</td>
                <td class="px-4 py-3">
                    <div class="text-slate-600">${sample.device_manufacturer}</div>
                    <div class="text-xs text-slate-500">${sample.device_model}</div>
                </td>
            `;
            tbody.appendChild(row);
        });
    
        lucide.createIcons();
        document.getElementById('resultCount').textContent = `Showing ${data.length} of ${SAMPLES_DATA.length} samples`;
    }

    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('mobile-overlay');
        
        if (sidebar.classList.contains('-translate-x-full')) {
            sidebar.classList.remove('-translate-x-full');
            overlay.classList.remove('hidden');
        } else {
            sidebar.classList.add('-translate-x-full');
            overlay.classList.add('hidden');
        }
    }

    function filterTable() {
        const term = document.getElementById('searchInput').value.toLowerCase();
        const filtered = SAMPLES_DATA.filter(sample => 
            sample.name.toLowerCase().includes(term) || 
            sample.location.toLowerCase().includes(term)
        );
        renderTable(filtered);
    }

    window.filterTable = filterTable;
});
