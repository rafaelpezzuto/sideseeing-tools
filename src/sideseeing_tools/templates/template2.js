/**
 * =================================================================
 * FUNÇÃO DA SIDEBAR (MODIFICADA PARA ATUALIZAR PLOTLY E LEAFLET)
 * =================================================================
 */
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    const activeSection = document.getElementById(sectionId);
    if (!activeSection) return;

    activeSection.classList.add('active');
    
    const activeLink = document.querySelector(`.sidebar .nav-link[onclick="showSection('${sectionId}')"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }

    // Atraso para garantir que a seção esteja visível antes de redimensionar
    setTimeout(() => {
        // 1. Redimensiona gráficos Plotly (Lógica original de Sensores)
        const plotlyCharts = activeSection.querySelectorAll('.plotly-chart');
        plotlyCharts.forEach(chartDiv => {
            if (chartDiv.data) { // Verifica se o Plotly já renderizou
                Plotly.Plots.resize(chartDiv);
            }
        });

        // 2. Redimensiona mapas Leaflet (Nova lógica para Wi-Fi)
        const leafletMaps = activeSection.querySelectorAll('.leaflet-map-container');
        leafletMaps.forEach(mapDiv => {
            const mapId = mapDiv.getAttribute('data-map-id'); //
            if (mapId && activeMaps[mapId]) {
                activeMaps[mapId].invalidateSize(); //
            }
        });
    }, 150);
}


// Cache global para instâncias de mapa Leaflet (necessário para redimensionar)
let activeMaps = {};


/**
 * =================================================================
 * LÓGICA DE CARREGAMENTO QUANDO O DOM ESTIVER PRONTO
 * =================================================================
 */
document.addEventListener('DOMContentLoaded', function() {
    
    /**
     * =================================================================
     * SEÇÃO: LÓGICA DE SENSORES (Original)
     * =================================================================
     */
    
    let loadedSamplesData = {}; // Cache para dados de sensores

    const selectElement = document.getElementById('sensor-select');
    const addSampleBtn = document.getElementById('add-sample-btn');
    const resetViewBtn = document.getElementById('reset-view-btn');
    
    const chartsContainer = document.getElementById('charts-container');
    const spinner = document.getElementById('charts-spinner');
    const placeholder = document.getElementById('charts-placeholder');
    const checkboxesContainer = document.getElementById('sensor-checkboxes-container');
    const checkboxesList = document.getElementById('sensor-checkboxes-list');
    const checkAllBtn = document.getElementById('check-all-sensors');
    const uncheckAllBtn = document.getElementById('uncheck-all-sensors');

    if (selectElement) { // Só executa se a seção de sensor existir
        addSampleBtn.addEventListener('click', handleAddSampleClick); //
        resetViewBtn.addEventListener('click', handleResetView); //
        checkboxesList.addEventListener('change', handleCheckboxChange); //
        checkAllBtn.addEventListener('click', () => toggleAllCheckboxes(true)); //
        uncheckAllBtn.addEventListener('click', () => toggleAllCheckboxes(false)); //
    }

    function handleAddSampleClick() {
        const selectedOption = selectElement.options[selectElement.selectedIndex]; //
        if (!selectedOption || !selectedOption.value) return;
        const jsonPath = selectedOption.value; //
        const sampleName = selectedOption.textContent; //
        if (loadedSamplesData[jsonPath]) { //
            alert("Esta amostra já foi adicionada.");
            return;
        }
        placeholder.style.display = 'none'; //
        spinner.classList.remove('d-none'); //
        spinner.classList.add('d-flex'); //
        
        fetch(jsonPath) //
            .then(response => {
                if (!response.ok) throw new Error(`Falha ao carregar ${jsonPath}`);
                return response.json();
            })
            .then(chartsData => {
                loadedSamplesData[jsonPath] = { name: sampleName, data: chartsData }; //
                spinner.classList.add('d-none'); //
                spinner.classList.remove('d-flex'); //
                populateSensorCheckboxes(jsonPath, sampleName, chartsData); //
                checkboxesContainer.style.display = 'block'; //
                renderSelectedCharts(); //
            })
            .catch(handleFetchError); //
    }

    function handleResetView() {
        loadedSamplesData = {}; //
        chartsContainer.innerHTML = ''; //
        checkboxesList.innerHTML = ''; //
        checkboxesContainer.style.display = 'none'; //
        placeholder.style.display = 'block'; //
        selectElement.value = ''; //
    }

    function handleCheckboxChange(event) {
        if (event.target.classList.contains('sensor-toggle-checkbox')) { //
            renderSelectedCharts(); //
        }
    }

    function populateSensorCheckboxes(jsonPath, sampleName, chartsData) {
        if (chartsData.length === 0) { //
            checkboxesList.innerHTML += `<p class="text-muted">Nenhum sensor encontrado na amostra ${sampleName}.</p>`;
            return;
        }
        const sampleGroup = document.createElement('div'); //
        sampleGroup.className = 'sample-checkbox-group mb-2 p-2 border rounded'; //
        let groupHTML = `<strong class="d-block mb-2">${sampleName}</strong>`; //
        chartsData.forEach((chart, index) => {
            const title = chart.layout.title ? chart.layout.title.replace(/<b>Sensor:<\/b>\s*/i, '') : `Sensor ${index + 1}`; //
            const chartId = chart.chart_id; //
            groupHTML += `
                <div class="form-check form-check-inline">
                    <input class="form-check-input sensor-toggle-checkbox" 
                           type="checkbox" value="${chartId}" id="chk-${chartId}"
                           data-sample-path="${jsonPath}" data-sensor-name="${title}"> 
                    <label class="form-check-label" for="chk-${chartId}">${title}</label>
                </div>`; //
        });
        sampleGroup.innerHTML = groupHTML; //
        checkboxesList.appendChild(sampleGroup); //
    }

    function renderSelectedCharts() {
        chartsContainer.innerHTML = ''; //
        const checkedBoxes = checkboxesList.querySelectorAll('.sensor-toggle-checkbox:checked'); //
        if (checkedBoxes.length === 0) {
            chartsContainer.innerHTML = '<p class="text-center text-muted fs-5">Nenhum sensor selecionado para exibição.</p>';
            return;
        }
        checkedBoxes.forEach(checkbox => {
            const chartId = checkbox.value; //
            const samplePath = checkbox.dataset.samplePath;  //
            const sample = loadedSamplesData[samplePath]; //
            if (!sample) return; 
            const chartData = sample.data.find(c => c.chart_id === chartId); //
            if (chartData) {
                const chartDiv = document.createElement('div'); //
                chartDiv.id = chartData.chart_id;  //
                chartDiv.className = 'col-12 col-lg-6 mb-4 plotly-chart';  //
                chartDiv.style.width = '100%';
                chartDiv.style.height = '450px';
                chartsContainer.appendChild(chartDiv); //
                const newLayout = { ...chartData.layout }; //
                const originalTitle = newLayout.title || 'Sensor'; //
                const sampleName = sample.name; //
                newLayout.title = `${originalTitle}<br><span style="font-size:0.8em; color: #555;">Amostra: ${sampleName}</span>`; //
                Plotly.newPlot(chartDiv, chartData.data, newLayout, { responsive: true }); //
            }
        });
    }

    function toggleAllCheckboxes(checkedState) {
        const checkboxes = checkboxesList.querySelectorAll('.sensor-toggle-checkbox'); //
        checkboxes.forEach(chk => {
            chk.checked = checkedState; //
        });
        renderSelectedCharts(); //
    }

    function handleFetchError(error) {
        console.error('Erro ao carregar dados do sensor:', error); //
        spinner.classList.add('d-none'); //
        spinner.classList.remove('d-flex'); //
        chartsContainer.innerHTML = `<div class="alert alert-danger">Falha ao carregar dados da amostra.</div>`; //
    }


    /**
     * =================================================================
     * SEÇÃO: LÓGICA DE WI-FI (MODIFICADA)
     * =================================================================
     */

    let loadedWifiData = {}; // Cache para dados de Wi-Fi

    const wifiSelect = document.getElementById('wifi-select');
    const addWifiBtn = document.getElementById('add-wifi-sample-btn');
    const resetWifiBtn = document.getElementById('reset-wifi-view-btn');
    
    const wifiControlsContainer = document.getElementById('wifi-controls-container');
    const wifiControlsList = document.getElementById('wifi-controls-list');
    const wifiMapContainer = document.getElementById('wifi-map-container');
    const wifiSpinner = document.getElementById('wifi-map-spinner');
    const wifiPlaceholder = document.getElementById('wifi-map-placeholder');
    
    if (wifiSelect) { // Só executa se a seção de Wi-Fi existir
        
        addWifiBtn.addEventListener('click', handleAddWifiSample); //
        resetWifiBtn.addEventListener('click', handleResetWifiView); //
        
        // --- MODIFICADO ---
        // Um listener de clique para tratar todos os botões (Plotar, Mostrar Todos, Esconder Todos)
        wifiControlsList.addEventListener('click', handleWifiGlobalClick); //
        
        // Listener para as barras de pesquisa (keyup)
        wifiControlsList.addEventListener('keyup', handleWifiSearch); //
    }

    /**
     * NOVO: Listener de clique global para a área de controles de Wi-Fi.
     * Delega a ação para a função correta.
     */
    function handleWifiGlobalClick(event) {
        const target = event.target;
        
        // Se clicou no botão "Plotar"
        if (target.classList.contains('plot-wifi-btn')) { //
            handleWifiControlClick(target); // Chama a função de plotar
        }
        // Se clicou no botão "Mostrar Todos"
        else if (target.classList.contains('wifi-show-all-btn')) { //
            handleShowAllWifi(target); // Chama a nova função de mostrar tudo
        }
        // --- INÍCIO DA MODIFICAÇÃO ---
        // Se clicou no botão "Esconder Todos"
        else if (target.classList.contains('wifi-hide-all-btn')) {
            handleHideAllWifi(target); // Chama a nova função de esconder
        }
        // --- FIM DA MODIFICAÇÃO ---
    }

    /**
     * NOVO: Mostra todos os SSIDs para uma determinada amostra.
     */
    function handleShowAllWifi(button) {
        const listId = button.dataset.listId; //
        const listElement = document.getElementById(listId);
        if (!listElement) return;

        const items = listElement.querySelectorAll('.wifi-ssid-item'); //
        items.forEach(item => {
            item.style.display = 'block'; // Força a exibição de todos
        });
    }

    /**
     * --- INÍCIO DA MODIFICAÇÃO ---
     * NOVO: Esconde todos os SSIDs e limpa a pesquisa.
     */
    function handleHideAllWifi(button) {
        const listId = button.dataset.listId;
        const listElement = document.getElementById(listId);
        if (!listElement) return;

        // 1. Esconde todos os itens
        const items = listElement.querySelectorAll('.wifi-ssid-item');
        items.forEach(item => {
            item.style.display = 'none'; // Esconde
        });

        // 2. Limpa o campo de pesquisa associado
        // O campo de pesquisa está no mesmo 'sampleGroup' (elemento pai)
        const sampleGroup = button.closest('.sample-wifi-group'); //
        if (sampleGroup) {
            const searchBar = sampleGroup.querySelector('.wifi-search-bar'); //
            if (searchBar) {
                searchBar.value = '';
            }
        }
    }
    /**
     * --- FIM DA MODIFICAÇÃO ---
     */


    /**
     * MODIFICADO: Filtra a lista de SSIDs E esconde se a busca estiver vazia.
     */
    function handleWifiSearch(event) {
        // Só executa se o evento veio de uma barra de pesquisa
        if (!event.target.classList.contains('wifi-search-bar')) return; //

        const input = event.target;
        const filterText = input.value.toLowerCase(); //
        const listId = input.dataset.listId; //
        const listElement = document.getElementById(listId);

        if (!listElement) return;

        const items = listElement.querySelectorAll('.wifi-ssid-item'); //
        
        items.forEach(item => {
            const ssidName = item.dataset.ssidName; //

            // --- LÓGICA MODIFICADA ---
            // 1. Se a barra de pesquisa estiver vazia, esconde o item
            if (filterText === "") { //
                item.style.display = 'none'; //
            } 
            // 2. Se não estiver vazia E der match, mostra
            else if (ssidName.includes(filterText)) { //
                item.style.display = 'block'; // Mostra o item
            } 
            // 3. Se não der match, esconde
            else {
                item.style.display = 'none'; // Esconde o item
            }
        });
    }

    /**
     * Carrega o JSON de Wi-Fi para uma amostra
     */
    function handleAddWifiSample() {
        const selectedOption = wifiSelect.options[wifiSelect.selectedIndex]; //
        if (!selectedOption || !selectedOption.value) return;

        const jsonPath = selectedOption.value; //
        const sampleName = selectedOption.textContent; //

        if (loadedWifiData[jsonPath]) { //
            alert("Esta amostra já foi adicionada.");
            return;
        }

        wifiPlaceholder.style.display = 'none'; //
        wifiSpinner.classList.remove('d-none'); //
        wifiSpinner.classList.add('d-flex'); //
        
        fetch(jsonPath) //
            .then(response => {
                if (!response.ok) throw new Error(`Falha ao carregar ${jsonPath}`);
                return response.json();
            })
            .then(wifiData => {
                // Armazena dados no cache
                loadedWifiData[jsonPath] = { name: sampleName, data: wifiData }; //
                
                wifiSpinner.classList.add('d-none'); //
                wifiSpinner.classList.remove('d-flex'); //
                
                // Cria os botões de controle (ex: Plotar "eduroam" 2.4Ghz)
                populateWifiControls(jsonPath, sampleName, wifiData); //
                
                wifiControlsContainer.style.display = 'block'; //
            })
            .catch(err => {
                console.error("Erro ao carregar dados Wi-Fi:", err);
                wifiSpinner.classList.add('d-none'); //
                wifiMapContainer.innerHTML = `<div class="alert alert-danger">Falha ao carregar dados da amostra.</div>`; //
            });
    }

    /**
     * Limpa a visualização de Wi-Fi
     */
    function handleResetWifiView() {
        loadedWifiData = {}; //
        activeMaps = {}; // Limpa o cache de mapas
        wifiControlsList.innerHTML = ''; //
        wifiMapContainer.innerHTML = ''; // Limpa mapas
        wifiControlsContainer.style.display = 'none'; //
        wifiMapContainer.appendChild(wifiPlaceholder); // Restaura o placeholder
        wifiPlaceholder.style.display = 'block'; //
        wifiSelect.value = ''; //
    }

    /**
     * --- INÍCIO DA MODIFICAÇÃO ---
     * MODIFICADO: Cria botões, barra de pesquisa, e layout de GRIDE.
     */
    function populateWifiControls(jsonPath, sampleName, wifiData) {
        // wifiData tem o formato: {'SSID_Name': {'2.4GHz': [[...]], '5GHz': [[...]]}, ...}
        const ssids = Object.keys(wifiData); //
        
        const sampleGroupId = `wifi-group-${sampleName.replace(/[^a-zA-Z0.9]/g, '_')}`;

        const sampleGroup = document.createElement('div'); //
        sampleGroup.className = 'sample-wifi-group mb-3 p-2 border rounded'; //
        
        // ID único para a lista de SSIDs desta amostra
        const listId = `wifi-list-${sampleName.replace(/[^a-zA-Z0.9]/g, '_')}`;

        let groupHTML = `<strong class="d-block mb-2">${sampleName}</strong>`;
        
        // 1. Adiciona a barra de pesquisa
        groupHTML += `
            <input type="text" 
                   class="form-control form-control-sm mb-2 wifi-search-bar" 
                   placeholder="Digite para filtrar SSIDs..."
                   aria-label="Filtrar SSIDs para ${sampleName}"
                   data-list-id="${listId}"> 
        `; // O 'data-list-id' diz ao input qual lista ele deve filtrar

        // 2. Adiciona os botões "Mostrar Todos" e "Esconder Todos"
        groupHTML += `
            <button class="btn btn-sm btn-outline-secondary mb-2 wifi-show-all-btn"
                    data-list-id="${listId}">
                Mostrar Todos
            </button>
            <button class="btn btn-sm btn-outline-secondary mb-2 wifi-hide-all-btn"
                    data-list-id="${listId}">
                Esconder Todos
            </button>
        `;

        // 3. Adiciona a div que conterá a lista (AGORA COM A CLASSE DO GRID)
        //
        groupHTML += `<div id="${listId}" class="wifi-ssid-list-grid" style="max-height: 250px; overflow-y: auto;">`;

        if (ssids.length === 0) { //
            groupHTML += `<p class="text-muted">Nenhum SSID encontrado na amostra ${sampleName}.</p>`;
        } else {
            ssids.sort().forEach(ssid => {
                const bands = Object.keys(wifiData[ssid]); //
                
                // 4. 'wifi-ssid-item' é o contêiner E COMEÇA ESCONDIDO (display: none)
                groupHTML += `<div class="mb-2 wifi-ssid-item" data-ssid-name="${ssid.toLowerCase()}" style="display: none;">
                                <span class="fw-bold">${ssid}</span>: `; //
                
                bands.forEach(band => {
                    const mapId = `map-${sampleName.replace(/[^a-zA-Z0.9]/g, '_')}-${ssid.replace(/[^a-zA-Z0.9]/g, '_')}-${band}`; //
                    
                    groupHTML += `
                        <button class="btn btn-sm btn-outline-primary plot-wifi-btn"
                                data-json-path="${jsonPath}"
                                data-ssid="${ssid}"
                                data-band="${band}"
                                data-map-id="${mapId}">
                            Plotar ${band}
                        </button>
                    `; //
                });
                groupHTML += `</div>`; // Fim de wifi-ssid-item
            });
        }
        
        groupHTML += `</div>`; // Fim da div da lista
        
        // --- FIM DA MODIFICAÇÃO ---

        sampleGroup.innerHTML = groupHTML; //
        wifiControlsList.appendChild(sampleGroup); //
    }
    /**
     * --- FIM DA MODIFICAÇÃO ---
     */


    /**
     * Lida com o clique em um botão "Plotar" (NÃO MODIFICADO, AGORA CHAMADO PELO 'handleWifiGlobalClick')
     */
    function handleWifiControlClick(button) {
        // Esta função só é chamada se o target for 'plot-wifi-btn'
        // const button = event.target; //
        const { jsonPath, ssid, band, mapId } = button.dataset; //

        // Se o mapa já existe, não faz nada (ou podemos focar nele)
        if (activeMaps[mapId]) { //
            document.getElementById(mapId).scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }

        // 1. Pega os dados do cache
        const sampleData = loadedWifiData[jsonPath]; //
        if (!sampleData) return;
        const heatData = sampleData.data[ssid][band]; // Formato: [[lat, lon, level], ...]
        if (!heatData || heatData.length === 0) { //
            alert(`Nenhum dado encontrado para ${ssid} (${band}).`);
            return;
        }
        
        // 2. Cria os contêineres do mapa
        const mapWrapper = document.createElement('div'); //
        mapWrapper.id = mapId; //
        mapWrapper.className = 'col-12 col-lg-6 mb-4'; // Metade da tela
        
        const title = document.createElement('h5'); //
        title.className = 'text-center'; //
        title.innerHTML = `${ssid} (${band})<br><span style="font-size:0.8em; color: #555;">Amostra: ${sampleData.name}</span>`; //
        
        const mapInnerDiv = document.createElement('div'); //
        mapInnerDiv.className = 'leaflet-map-container'; //
        mapInnerDiv.setAttribute('data-map-id', mapId); // Referência para o showSection

        mapWrapper.appendChild(title); //
        mapWrapper.appendChild(mapInnerDiv); //
        wifiMapContainer.appendChild(mapWrapper); //

        // --- 3. Lógica de Plotagem (recriando plot_map de wifi-zones.ipynb) ---
        
        // 3a. Calcular centro e normalizar dados
        let centerLat = 0;
        let centerLon = 0;
        const levels = heatData.map(p => p[2]); // Pega todos os 'level'
        const minLevel = Math.min(...levels); // ex: -90
        const maxLevel = Math.max(...levels); // ex: -50
        const range = maxLevel - minLevel; //

        const normalizedHeatData = heatData.map(point => {
            const [lat, lon, level] = point;
            centerLat += lat;
            centerLon += lon;
            
            // Normaliza a intensidade (level) de 0.0 a 1.0
            // Leaflet.heat espera 'intensity' entre 0.0 (frio) e 1.0 (quente)
            let intensity = 0.5; // Caso padrão se houver só 1 ponto
            if (range > 0) {
                intensity = (level - minLevel) / range; //
            }
            return [lat, lon, intensity]; //
        });
        centerLat /= heatData.length; //
        centerLon /= heatData.length; //

        // 3b. Criar o mapa Leaflet
        const map = L.map(mapInnerDiv).setView([centerLat, centerLon], 18); //

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxNativeZoom: 19, // Define o zoom máximo dos tiles do provedor
            maxZoom: 22        // Define o zoom máximo permitido no mapa (over-zoom)
        }).addTo(map);

        // 3c. Adicionar o HeatMap (replicando folium.plugins.HeatMap)
        L.heatLayer(normalizedHeatData, {
            radius: 15, //
            blur: 10,   //
        }).addTo(map); //

        // 4. Salva a instância do mapa no cache global
        activeMaps[mapId] = map; //

        // 5. Força o mapa a redimensionar
        setTimeout(() => map.invalidateSize(), 10);
    }

});