/**
 * =================================================================
 * ARQUIVO: template.js
 * DESCRIÇÃO: Script principal para manipulação da interface,
 * carregamento de dados e plotagem de gráficos (Plotly) e
 * mapas (Leaflet) para as seções de Sensores e Wi-Fi.
 * =================================================================
 */

/**
 * Cache global para instâncias ativas do Leaflet.
 * Isso é necessário para que a função showSection possa chamar
 * .invalidateSize() em mapas que estão em abas escondidas.
 */
let activeMaps = {};

/**
 * =================================================================
 * FUNÇÃO GLOBAL DA SIDEBAR
 * =================================================================
 */

/**
 * Alterna a visibilidade das seções principais (abas).
 * Garante que gráficos Plotly e mapas Leaflet sejam redimensionados
 * corretamente após a aba se tornar visível.
 *
 * @param {string} sectionId O ID da div da seção a ser mostrada.
 */
function showSection(sectionId) {
    // 1. Esconde todas as seções e desativa todos os links
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        link.classList.remove('active');
    });

    // 2. Mostra a seção e ativa o link correspondente
    const activeSection = document.getElementById(sectionId);
    if (!activeSection) return;
    activeSection.classList.add('active');

    const activeLink = document.querySelector(`.sidebar .nav-link[onclick="showSection('${sectionId}')"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }

    // 3. Redimensiona gráficos e mapas
    // Usa um pequeno atraso (setTimeout) para garantir que a transição
    // do CSS (display: none -> block) tenha terminado
    // antes de tentar redimensionar os plots.
    setTimeout(() => {
        // 3a. Redimensiona gráficos Plotly
        const plotlyCharts = activeSection.querySelectorAll('.plotly-chart');
        plotlyCharts.forEach(chartDiv => {
            if (chartDiv.data) { // Verifica se o Plotly já renderizou
                Plotly.Plots.resize(chartDiv);
            }
        });

        // 3b. Redimensiona mapas Leaflet
        const leafletMaps = activeSection.querySelectorAll('.leaflet-map-container');
        leafletMaps.forEach(mapDiv => {
            const mapId = mapDiv.getAttribute('data-map-id');
            if (mapId && activeMaps[mapId]) { // Verifica se o mapa existe no cache
                activeMaps[mapId].invalidateSize();
            }
        });
    }, 150); // 150ms é um valor seguro para a transição
}

/**
 * =================================================================
 * PREENCHE ABA DE RESUMO
 * =================================================================
 */
function initSummaryTab(summaryData) {
    // Layout padrão para gráficos Plotly

    // 1. Renderizar Mapa de Visão Geral com Cluster
    try {
        // CORREÇÃO 1: Pegamos os dados completos (incluindo o 'name')
        const geoPointsData = summaryData.geo_centers_map || [];
        // Convertemos para o formato [lat, lon] apenas para calcular os limites
        const geoPointsCoords = geoPointsData.map(point => [point.lat, point.lon]);

        const mapDiv = document.getElementById('summary-overview-map');
        
        let mapCenter = [-23.5505, -46.6333]; // Padrão
        let mapZoom = 10; // Padrão
        let initialBounds = null; // Limites iniciais
        
        if (geoPointsCoords.length > 0) {
            initialBounds = L.latLngBounds(geoPointsCoords).pad(0.1); 
            mapCenter = initialBounds.getCenter(); 
        }

        const overviewMap = L.map(mapDiv).setView(mapCenter, mapZoom);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(overviewMap);

        // NOVO: Iteramos sobre os DADOS (geoPointsData) em vez das coordenadas
        geoPointsData.forEach(point => {
            const latLng = [point.lat, point.lon];
            const sampleName = point.name || 'Amostra'; // Nome da amostra

            const marker = L.marker(latLng);
            
            // ATUALIZAÇÃO 1: Adiciona o popup com o nome da amostra
            marker.bindPopup(`<b>Amostra:</b><br>${sampleName}`); 

            // ATUALIZAÇÃO 2: Lógica de clique atualizada
            marker.on('click', function(e) {
                const targetCenter = e.latlng;
                const targetZoom = 17;
                const currentCenter = overviewMap.getCenter();
                const currentZoom = overviewMap.getZoom();

                // Verificação para evitar o "tremor" (jitter)
                // Só "voa" se o mapa não estiver já centralizado (< 1 metro de distância)
                // ou se o zoom for diferente.
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

        // Criação do Botão de Recentralizar (Leaflet Control)
        const RecenterControl = L.Control.extend({
            options: {
                position: 'topright' 
            },
            onAdd: function(map) {
                const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
                
                // ATUALIZAÇÃO 3: Troca do ícone
                container.innerHTML = '&#x27f3;';
                container.title = "Recentralizar Mapa";
                
                container.style.backgroundColor = 'white';
                container.style.width = '30px';
                container.style.height = '30px';
                container.style.textAlign = 'center';
                container.style.lineHeight = '30px';
                container.style.fontSize = '1.6rem'; // Ajustado para o novo ícone
                container.style.fontWeight = 'bold'; // Deixa o ícone mais visível
                container.style.cursor = 'pointer';

                L.DomEvent.disableClickPropagation(container);

                L.DomEvent.on(container, 'click', function() {
                    if (initialBounds) {
                        map.flyToBounds(initialBounds);
                    } else {
                        map.flyTo(mapCenter, mapZoom);
                    }
                });

                return container;
            }
        });

        new RecenterControl().addTo(overviewMap);

    } catch (e) { console.error("Erro ao renderizar mapa de visão geral:", e); }
}

/**
 * =================================================================
 * PONTO DE ENTRADA PRINCIPAL (DOM PRONTO)
 * =================================================================
 */
document.addEventListener('DOMContentLoaded', function() {

    /**
     * =================================================================
     * SEÇÃO: LÓGICA DE SENSORES
     * =================================================================
     */

    // Cache para armazenar os dados JSON das amostras de sensores já carregadas
    let loadedSamplesData = {};

    /** ----------------------------------
     * DOM Elements (Sensores)
     * ---------------------------------- */
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

    // Só adiciona os listeners se os elementos da seção de sensores existirem
    if (selectElement) {
        /** ----------------------------------
         * Event Listeners (Sensores)
         * ---------------------------------- */
        addSampleBtn.addEventListener('click', handleAddSampleClick);
        resetViewBtn.addEventListener('click', handleResetView);
        checkboxesList.addEventListener('change', handleCheckboxChange);
        checkAllBtn.addEventListener('click', () => toggleAllCheckboxes(true));
        uncheckAllBtn.addEventListener('click', () => toggleAllCheckboxes(false));
    }

    /**
     * Manipula o clique no botão "Adicionar Amostra" (Sensores).
     * Carrega o arquivo JSON da amostra selecionada, armazena em cache,
     * e chama as funções para popular os checkboxes e renderizar os gráficos.
     */
    function handleAddSampleClick() {
        const selectedOption = selectElement.options[selectElement.selectedIndex];
        if (!selectedOption || !selectedOption.value) return;

        const jsonPath = selectedOption.value;
        const sampleName = selectedOption.textContent;

        // Evita recarregar a mesma amostra
        if (loadedSamplesData[jsonPath]) {
            alert("Esta amostra já foi adicionada.");
            return;
        }

        // Ativa o spinner e esconde o placeholder
        placeholder.style.display = 'none';
        spinner.classList.remove('d-none');
        spinner.classList.add('d-flex');

        // Busca os dados
        fetch(jsonPath)
            .then(response => {
                if (!response.ok) throw new Error(`Falha ao carregar ${jsonPath}`);
                return response.json();
            })
            .then(chartsData => {
                // Armazena no cache
                loadedSamplesData[jsonPath] = { name: sampleName, data: chartsData };
                
                spinner.classList.add('d-none');
                spinner.classList.remove('d-flex');
                
                // Cria os checkboxes para os sensores desta amostra
                populateSensorCheckboxes(jsonPath, sampleName, chartsData);
                checkboxesContainer.style.display = 'block';
                
                // Renderiza os gráficos (se algum estiver marcado por padrão, o que não é o caso aqui)
                renderSelectedCharts();
            })
            .catch(handleFetchError);
    }

    /**
     * Limpa a visualização dos sensores.
     * Reseta o cache, limpa os gráficos e checkboxes, e restaura o placeholder.
     */
    function handleResetView() {
        loadedSamplesData = {};
        chartsContainer.innerHTML = '';
        checkboxesList.innerHTML = '';
        checkboxesContainer.style.display = 'none';
        chartsContainer.appendChild(placeholder);
        placeholder.style.display = 'block';
        selectElement.value = '';
    }

    /**
     * Listener para qualquer mudança nos checkboxes de sensores.
     * Se um checkbox de sensor for (des)marcado, chama a renderização.
     * @param {Event} event O objeto do evento 'change'.
     */
    function handleCheckboxChange(event) {
        // Garante que o evento veio de um checkbox de sensor
        if (event.target.classList.contains('sensor-toggle-checkbox')) {
            renderSelectedCharts();
        }
    }

    /**
     * Cria e adiciona o grupo de checkboxes para uma amostra recém-carregada.
     * @param {string} jsonPath - O caminho para o JSON, usado como ID no cache.
     * @param {string} sampleName - O nome da amostra (para o título).
     * @param {Array} chartsData - O array de dados de gráficos vindo do JSON.
     */
    function populateSensorCheckboxes(jsonPath, sampleName, chartsData) {
        if (chartsData.length === 0) {
            checkboxesList.innerHTML += `<p class="text-muted">Nenhum sensor encontrado na amostra ${sampleName}.</p>`;
            return;
        }

        const sampleGroup = document.createElement('div');
        sampleGroup.className = 'sample-checkbox-group mb-2 p-2 border rounded';

        // Título do grupo
        let groupHTML = `<strong class="d-block mb-2">${sampleName}</strong>`;

        // Cria um checkbox para cada sensor (gráfico)
        chartsData.forEach((chart, index) => {
            // Extrai o nome do sensor do título do gráfico
            const title = chart.layout.title ? chart.layout.title.replace(/<b>Sensor:<\/b>\s*/i, '') : `Sensor ${index + 1}`;
            const chartId = chart.chart_id;
            
            groupHTML += `
                <div class="form-check form-check-inline">
                    <input class="form-check-input sensor-toggle-checkbox" 
                           type="checkbox" value="${chartId}" id="chk-${chartId}"
                           data-sample-path="${jsonPath}" data-sensor-name="${title}"> 
                    <label class="form-check-label" for="chk-${chartId}">${title}</label>
                </div>`;
        });

        sampleGroup.innerHTML = groupHTML;
        checkboxesList.appendChild(sampleGroup);
    }

    /**
     * Renderiza os gráficos Plotly com base nos checkboxes marcados.
     * Limpa o contêiner e redesenha todos os gráficos selecionados.
     */
    function renderSelectedCharts() {
        chartsContainer.innerHTML = ''; // Limpa a área de gráficos
        const checkedBoxes = checkboxesList.querySelectorAll('.sensor-toggle-checkbox:checked');

        if (checkedBoxes.length === 0) {
            chartsContainer.innerHTML = '<p class="text-center text-muted fs-5">Nenhum sensor selecionado para exibição.</p>';
            return;
        }

        checkedBoxes.forEach(checkbox => {
            const chartId = checkbox.value;
            const samplePath = checkbox.dataset.samplePath;
            const sample = loadedSamplesData[samplePath];
            if (!sample) return;

            // Encontra o dado do gráfico específico dentro da amostra
            const chartData = sample.data.find(c => c.chart_id === chartId);
            if (chartData) {
                // Cria a div para o gráfico
                const chartDiv = document.createElement('div');
                chartDiv.id = chartData.chart_id;
                chartDiv.className = 'col-12 col-lg-6 mb-4 plotly-chart';
                chartDiv.style.width = '100%';
                chartDiv.style.height = '450px';
                chartsContainer.appendChild(chartDiv);
                
                // Adiciona o nome da amostra ao título do gráfico
                const newLayout = { ...chartData.layout };
                const originalTitle = newLayout.title || 'Sensor';
                const sampleName = sample.name;
                newLayout.title = `${originalTitle}<br><span style="font-size:0.8em; color: #555;">Amostra: ${sampleName}</span>`;

                // Plota o gráfico
                Plotly.newPlot(chartDiv, chartData.data, newLayout, { responsive: true });
            }
        });
    }

    /**
     * Marca ou desmarca todos os checkboxes de sensores.
     * @param {boolean} checkedState - true para marcar todos, false para desmarcar.
     */
    function toggleAllCheckboxes(checkedState) {
        const checkboxes = checkboxesList.querySelectorAll('.sensor-toggle-checkbox');
        checkboxes.forEach(chk => {
            chk.checked = checkedState;
        });
        renderSelectedCharts(); // Atualiza a visualização
    }

    /**
     * Manipulador de erro genérico para o fetch de dados de sensores.
     * @param {Error} error O objeto de erro.
     */
    function handleFetchError(error) {
        console.error('Erro ao carregar dados do sensor:', error);
        spinner.classList.add('d-none');
        spinner.classList.remove('d-flex');
        chartsContainer.innerHTML = `<div class="alert alert-danger">Falha ao carregar dados da amostra.</div>`;
    }

/**
     * =================================================================
     * SEÇÃO: LÓGICA DE WI-FI 
     * =================================================================
     */

    // Cache para armazenar os dados JSON das amostras de Wi-Fi já carregadas
    let loadedWifiData = {};

    /** ----------------------------------
     * DOM Elements (Wi-Fi)
     * ---------------------------------- */
    const wifiSelect = document.getElementById('wifi-select');
    const addWifiBtn = document.getElementById('add-wifi-sample-btn');
    const resetWifiBtn = document.getElementById('reset-wifi-view-btn');
    
    // Contêineres da Etapa 2 (Seleção de SSID)
    const wifiSsidControlsContainer = document.getElementById('wifi-ssid-controls-container');
    const wifiSsidListContainer = document.getElementById('wifi-ssid-list-container');
    
    // Contêineres da Etapa 3 (Seleção de Banda)
    const wifiBandControlsContainer = document.getElementById('wifi-band-controls-container');
    const wifiBandButtonsList = document.getElementById('wifi-band-buttons-list');

    // Contêineres do Mapa
    const wifiMapContainer = document.getElementById('wifi-map-container');
    const wifiSpinner = document.getElementById('wifi-map-spinner');
    const wifiPlaceholder = document.getElementById('wifi-map-placeholder');

    // Só adiciona os listeners se os elementos da seção de Wi-Fi existirem
    if (wifiSelect) {
        /** ----------------------------------
         * Event Listeners (Wi-Fi)
         * ---------------------------------- */
        addWifiBtn.addEventListener('click', handleAddWifiSample);
        resetWifiBtn.addEventListener('click', handleResetWifiView);

        // Delegação de eventos para os controles de Wi-Fi (Etapa 2):
        wifiSsidListContainer.addEventListener('click', handleWifiSsidListClick);
        
        // Um único listener 'keyup' trata todas as barras de pesquisa.
        wifiSsidListContainer.addEventListener('keyup', handleWifiSearch);

        // Delegação de eventos para os controles de Wi-Fi (Etapa 3):
        wifiBandButtonsList.addEventListener('click', handleWifiBandListClick);
    }

    /**
     * Manipulador de clique global (delegação de evento) para a lista de SSIDs (Etapa 2).
     * Identifica se o clique foi em uma caixa de SSID, "Mostrar Todos" ou "Esconder Todos".
     * @param {Event} event O objeto do evento 'click'.
     */
    function handleWifiSsidListClick(event) {
        const target = event.target;

        // Se clicou no botão "Mostrar Todos"
        if (target.classList.contains('wifi-show-all-btn')) {
            handleShowAllWifi(target);
            return;
        }
        // Se clicou no botão "Esconder Todos"
        if (target.classList.contains('wifi-hide-all-btn')) {
            handleHideAllWifi(target);
            return;
        }

        // Se clicou em uma caixa de SSID (ou seu filho)
        const ssidBox = target.closest('.ssid-selectable-box');
        if (ssidBox) {
            event.preventDefault(); // Impede o <a> de navegar
            handleSsidBoxClick(ssidBox); // Chama o handler da Etapa 3
        }
    }

    /**
     * Manipulador de clique (delegação) para os botões de Banda (Etapa 3).
     * @param {Event} event O objeto do evento 'click'.
     */
    function handleWifiBandListClick(event) {
        const target = event.target;
        // Se clicou no botão "Plotar [banda]"
        if (target.classList.contains('plot-wifi-btn')) {
            handleWifiControlClick(target); // Esta é a função antiga que plota o mapa
        }
    }

    /**
     * Remove um mapa específico (por ID) da tela e do cache.
     * Esta função é chamada pelo L.Control do botão fechar.
     * @param {string} mapIdToRemove O ID do wrapper do mapa (ex: 'map-wifi-...')
     */
    function handleCloseMap(mapIdToRemove) {
        const mapWrapperToRemove = document.getElementById(mapIdToRemove);

        if (mapWrapperToRemove) {
            // Remove o wrapper do mapa do DOM
            mapWrapperToRemove.remove();

            // Remove a instância do mapa do cache
            if (activeMaps[mapIdToRemove]) {
                activeMaps[mapIdToRemove].remove(); // Remove o mapa Leaflet
                delete activeMaps[mapIdToRemove];
            }
        }
        
        // Verifica se ainda há mapas visíveis (especificamente de Wi-Fi).
        // Um modo mais simples é checar quantos wrappers de mapa sobraram.
        const remainingMaps = wifiMapContainer.querySelectorAll('.leaflet-map-container').length;

        if (remainingMaps === 0 && Object.keys(activeMaps).length === 0) {
            // Se não houver mais mapas, mostra o placeholder
            wifiMapContainer.appendChild(wifiPlaceholder);
            wifiPlaceholder.style.display = 'block';
        }
        
        // Desmarca o botão de "Plotar Banda" correspondente
        const correspondingBandButton = document.querySelector(`.plot-wifi-btn[data-map-id="${mapIdToRemove}"]`);
        if (correspondingBandButton) {
            correspondingBandButton.classList.remove('btn-primary');
            correspondingBandButton.classList.add('btn-outline-primary');
        }
    }

    /**
     * Mostra todos os itens de SSID para uma amostra específica.
     * @param {HTMLElement} button O botão "Mostrar Todos" que foi clicado.
     */
    function handleShowAllWifi(button) {
        const listId = button.dataset.listId; // ID da lista de SSIDs
        const listElement = document.getElementById(listId);
        if (!listElement) return;

        const items = listElement.querySelectorAll('.wifi-ssid-item');
        items.forEach(item => {
            item.style.display = 'block'; // Força a exibição
        });
    }

    /**
     * Esconde todos os itens de SSID para uma amostra específica e limpa a barra de pesquisa.
     * @param {HTMLElement} button O botão "Esconder Todos" que foi clicado.
     */
    function handleHideAllWifi(button) {
        const listId = button.dataset.listId;
        const listElement = document.getElementById(listId);
        if (!listElement) return;

        // 1. Esconde todos os itens da lista
        const items = listElement.querySelectorAll('.wifi-ssid-item');
        items.forEach(item => {
            item.style.display = 'none';
        });

        // 2. Limpa o campo de pesquisa associado
        const sampleGroup = button.closest('.sample-wifi-group');
        if (sampleGroup) {
            const searchBar = sampleGroup.querySelector('.wifi-search-bar');
            if (searchBar) {
                searchBar.value = '';
            }
        }
    }

    /**
     * Filtra a lista de SSIDs com base no texto digitado na barra de pesquisa.
     * Lógica principal:
     * 1. Se a pesquisa estiver vazia, esconde TODOS os itens (para forçar o uso do filtro ou "Mostrar Todos").
     * 2. Se houver texto, mostra apenas os itens que dão match.
     * @param {Event} event O objeto do evento 'keyup'.
     */
    function handleWifiSearch(event) {
        // Garante que o evento veio de uma barra de pesquisa
        if (!event.target.classList.contains('wifi-search-bar')) return;

        const input = event.target;
        const filterText = input.value.toLowerCase(); // Texto da busca
        const listId = input.dataset.listId;         // Lista a ser filtrada
        const listElement = document.getElementById(listId);

        if (!listElement) return;

        const items = listElement.querySelectorAll('.wifi-ssid-item');

        items.forEach(item => {
            const ssidName = item.dataset.ssidName; // Nome do SSID (em minúsculas)

            if (filterText === "") {
                item.style.display = 'none';
            }
            else if (ssidName.includes(filterText)) {
                item.style.display = 'block';
            }
            else {
                item.style.display = 'none';
            }
        });
    }

    /**
     * Manipula o clique no botão "Adicionar Amostra" (Wi-Fi).
     * Carrega o arquivo JSON e chama a função para popular a Etapa 2.
     */
    function handleAddWifiSample() {
        const selectedOption = wifiSelect.options[wifiSelect.selectedIndex];
        if (!selectedOption || !selectedOption.value) return;

        const jsonPath = selectedOption.value;
        const sampleName = selectedOption.textContent;

        if (loadedWifiData[jsonPath]) {
            alert("Esta amostra já foi adicionada.");
            return;
        }

        wifiPlaceholder.style.display = 'none';
        wifiSpinner.classList.remove('d-none');
        wifiSpinner.classList.add('d-flex');

        fetch(jsonPath)
            .then(response => {
                if (!response.ok) throw new Error(`Falha ao carregar ${jsonPath}`);
                return response.json();
            })
            .then(wifiData => {
                loadedWifiData[jsonPath] = { name: sampleName, data: wifiData };
                
                wifiSpinner.classList.add('d-none');
                wifiSpinner.classList.remove('d-flex');
                
                // Cria a UI de controles (pesquisa, caixas de SSID) para esta amostra
                populateWifiSsidControls(jsonPath, sampleName, wifiData);
                
                wifiSsidControlsContainer.style.display = 'block';
            })
            .catch(err => {
                console.error("Erro ao carregar dados Wi-Fi:", err);
                wifiSpinner.classList.add('d-none');
                wifiMapContainer.innerHTML = `<div class="alert alert-danger">Falha ao carregar dados da amostra.</div>`;
            });
    }

    /**
     * Limpa a visualização de Wi-Fi.
     * Reseta caches, limpa mapas, e limpa as Etapas 2 e 3.
     */
    function handleResetWifiView() {
        loadedWifiData = {};

        // Remove cada instância de mapa Leaflet antes de limpar o DOM
        for (const mapId in activeMaps) {
            if (activeMaps[mapId]) {
                activeMaps[mapId].remove();
            }
        }

        activeMaps = {}; // Limpa o cache de mapas Leaflet
        
        wifiSsidListContainer.innerHTML = '';      // Limpa Etapa 2
        wifiBandButtonsList.innerHTML = '';        // Limpa Etapa 3
        wifiMapContainer.innerHTML = '';           // Limpa os mapas renderizados

        wifiSsidControlsContainer.style.display = 'none';
        wifiBandControlsContainer.style.display = 'none';
        
        // Recoloca o placeholder dentro do contêiner de mapas
        wifiMapContainer.appendChild(wifiPlaceholder);
        wifiPlaceholder.style.display = 'block';
        wifiSelect.value = '';
    }

    /**
     * Cria a UI de controle para uma amostra de Wi-Fi recém-carregada (Etapa 2).
     * Isso inclui: Título da amostra, Barra de Pesquisa, Botões "Mostrar/Esconder Todos",
     * e a lista (grid) de CAIXAS CLICÁVEIS para cada SSID.
     *
     * @param {string} jsonPath - O caminho para o JSON (ID do cache).
     * @param {string} sampleName - O nome da amostra (para o título).
     * @param {Object} wifiData - Os dados de Wi-Fi (formato: {'SSID': {'Banda': [[...]]}})
     */
    function populateWifiSsidControls(jsonPath, sampleName, wifiData) {
        const ssids = Object.keys(wifiData);
        
        const sampleGroup = document.createElement('div');
        sampleGroup.className = 'sample-wifi-group mb-3';
        
        // ID único para a *lista* de SSIDs desta amostra (para a pesquisa)
        const listId = `wifi-list-${sampleName.replace(/[^a-zA-Z0.9]/g, '_')}`;

        let groupHTML = `<strong class="d-block mb-2">${sampleName}</strong>`;
        
        // 1. Adiciona a barra de pesquisa
        groupHTML += `
            <input type="text" 
                   class="form-control form-control-sm mb-2 wifi-search-bar" 
                   placeholder="Digite para filtrar SSIDs... "
                   aria-label="Filtrar SSIDs para ${sampleName}"
                   data-list-id="${listId}"> `;

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

        // 3. Adiciona a div que conterá a lista (grid) de SSIDs
        groupHTML += `<div id="${listId}" class="wifi-ssid-list-grid">`;

        if (ssids.length === 0) {
            groupHTML += `<p class="text-muted">Nenhum SSID encontrado na amostra ${sampleName}.</p>`;
        } else {
            ssids.sort().forEach(ssid => {
                
                // 4. Contêiner para a caixa do SSID
                // Começa escondido (display: none)
                // (MUDANÇA: Não criamos mais botões de banda aqui)
                groupHTML += `
                    <div class="mb-2 wifi-ssid-item" 
                         data-ssid-name="${ssid.toLowerCase()}" 
                         style="display: none;">
                        
                        <a href="#" class="ssid-selectable-box"
                           data-json-path="${jsonPath}"
                           data-ssid="${ssid}"
                           onclick="return false;">
                            ${ssid}
                        </a>
                    </div>`;
            });
        }
        
        groupHTML += `</div>`; // Fim da div da lista (grid)
        
        sampleGroup.innerHTML = groupHTML;
        wifiSsidListContainer.appendChild(sampleGroup);
    }

    /**
     * NOVO: Manipula o clique em uma caixa de SSID (Etapa 2).
     * Popula a Etapa 3 com os botões de banda disponíveis.
     * @param {HTMLElement} ssidBox O elemento <a> clicado.
     */
    function handleSsidBoxClick(ssidBox) {
        const { jsonPath, ssid } = ssidBox.dataset;
        
        // 1. UI de Ativação: Remove 'active' de todas as caixas
        // e adiciona na clicada.
        document.querySelectorAll('.ssid-selectable-box').forEach(box => {
            box.classList.remove('active');
        });
        ssidBox.classList.add('active');

        // 2. Encontra os dados no cache
        const sample = loadedWifiData[jsonPath];
        if (!sample || !sample.data[ssid]) {
            console.error("Dados do SSID não encontrados no cache.", ssid, sample);
            return;
        }
        
        // Pega o nome da amostra (para o ID do mapa)
        const sampleName = sample.name;
        // Pega as bandas disponíveis (ex: ["2.4GHz", "5GHz"])
        const bands = Object.keys(sample.data[ssid]);

        // 3. Limpa botões de banda antigos (Etapa 3)
        wifiBandButtonsList.innerHTML = '';

        // 4. Cria os novos botões de banda
        bands.forEach(band => {
            // ID único para o mapa que será gerado
            const mapId = `map-${sampleName.replace(/[^a-zA-Z0.9]/g, '_')}-${ssid.replace(/[^a-zA-Z0.9]/g, '_')}-${band}`;
            
            const button = document.createElement('button');
            // Usamos 'btn-outline-primary' para que não pareçam ativos
            button.className = 'btn btn-outline-primary me-2 mb-2 plot-wifi-btn';
            button.textContent = `Plotar ${band}`;
            
            // Adiciona os data attributes para o handler 'handleWifiControlClick'
            button.dataset.jsonPath = jsonPath;
            button.dataset.ssid = ssid;
            button.dataset.band = band;
            button.dataset.mapId = mapId;
            
            wifiBandButtonsList.appendChild(button);
        });

        // 5. Mostra a Etapa 3
        wifiBandControlsContainer.style.display = 'block';
    }

    /**
     * Manipula o clique em um botão "Plotar [banda]" (Etapa 3).
     * Esta função é chamada pela delegação de evento `handleWifiBandListClick`.
     * Cria e renderiza um novo mapa de calor Leaflet.
     *
     * @param {HTMLElement} button O botão "plot-wifi-btn" que foi clicado.
     */
    function handleWifiControlClick(button) {
        // Pega os dados armazenados no botão
        const { jsonPath, ssid, band, mapId } = button.dataset;

        // UI de Ativação: Marca este botão como "ativo" e desmarca outros
        document.querySelectorAll('.plot-wifi-btn').forEach(btn => {
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-outline-primary');
        });
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-primary');


        // Se o mapa já foi plotado, apenas rola a tela até ele
        if (activeMaps[mapId]) {
            document.getElementById(mapId).scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }

        // 1. Pega os dados do cache
        const sampleData = loadedWifiData[jsonPath];
        if (!sampleData) return;
        
        // Formato: [[lat, lon, level], ...]
        const heatData = sampleData.data[ssid][band];
        if (!heatData || heatData.length === 0) {
            alert(`Nenhum dado encontrado para ${ssid} (${band}).`);
            return;
        }
        
        // 2. Cria os contêineres do mapa (Wrapper e Div interna)
        let mapWrapper = document.getElementById(mapId);
        if (mapWrapper) {
            mapWrapper.innerHTML = ''; 
        } else {
            mapWrapper = document.createElement('div');
            mapWrapper.id = mapId;
            // MUDANÇA: Adicionamos 'leaflet-map-wrapper' para consistência, 
            // embora o L.Control não precise dele para posicionamento.
            mapWrapper.className = 'col-12 col-lg-6 mb-4 leaflet-map-wrapper'; 
            wifiMapContainer.appendChild(mapWrapper);
        }
        
        const title = document.createElement('h5');
        title.className = 'text-center';
        title.innerHTML = `${ssid} (${band})<br><span style="font-size:0.8em; color: #555;">Amostra: ${sampleData.name}</span>`;
        
        const mapInnerDiv = document.createElement('div');
        mapInnerDiv.className = 'leaflet-map-container'; 
        mapInnerDiv.setAttribute('data-map-id', mapId); 

        mapWrapper.appendChild(title);
        mapWrapper.appendChild(mapInnerDiv);

        // MUDANÇA: Removemos o botão HTML antigo daqui.
        // O código 'const closeBtn = ...' foi removido.

        // 3. Lógica de Plotagem
        
        // 3a. Calcular centro e normalizar dados
        let centerLat = 0;
        let centerLon = 0;
        const levels = heatData.map(p => p[2]);
        const minLevel = Math.min(...levels);
        const maxLevel = Math.max(...levels);
        const range = maxLevel - minLevel;

        const normalizedHeatData = heatData.map(point => {
            const [lat, lon, level] = point;
            centerLat += lat;
            centerLon += lon;
            
            let intensity = 0.5; 
            if (range > 0) {
                intensity = (level - minLevel) / range;
            }
            return [lat, lon, intensity];
        });
        
        centerLat /= heatData.length;
        centerLon /= heatData.length;

        // 3b. Criar o mapa Leaflet
        const map = L.map(mapInnerDiv).setView([centerLat, centerLon], 18);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxNativeZoom: 19, 
            maxZoom: 22        
        }).addTo(map);

        // 3c. Adicionar a camada de HeatMap
        L.heatLayer(normalizedHeatData, {
            radius: 15, 
            blur: 10,   
        }).addTo(map);

        // 4. MUDANÇA: Adiciona o controle de "Fechar" (estilo Leaflet)
        const CloseControl = L.Control.extend({
            options: {
                position: 'topright' // Posição do controle
            },
            onAdd: function(map) {
                // Cria o container do botão
                const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control leaflet-control-custom');
                
                container.innerHTML = '&times;'; // 'X' (símbolo HTML)
                container.title = "Fechar este mapa";
                
                // Estilos (iguais ao da aba Resumo)
                container.style.backgroundColor = 'white';
                container.style.width = '30px';
                container.style.height = '30px';
                container.style.textAlign = 'center';
                container.style.lineHeight = '30px';
                container.style.fontSize = '1.8rem';
                container.style.fontWeight = 'bold';
                container.style.cursor = 'pointer';

                // Previne que o clique se propague para o mapa
                L.DomEvent.disableClickPropagation(container);

                // Adiciona o listener de clique
                L.DomEvent.on(container, 'click', function() {
                    // Chama a nossa nova função de fechar
                    handleCloseMap(mapId); 
                });

                return container;
            }
        });

        // Adiciona o novo controle ao mapa
        new CloseControl().addTo(map);

        // 5. Salva a instância do mapa no cache global
        activeMaps[mapId] = map;

        // 6. Força o mapa a redimensionar
        setTimeout(() => map.invalidateSize(), 10);
    }

    /**
     * =================================================================
     * SEÇÃO: LÓGICA GEOESPACIAL (GPS)
     * =================================================================
     */

    // Cache para armazenar os dados JSON das amostras GEO já carregadas
    let loadedGeoData = {};

    /** ----------------------------------
     * DOM Elements (Geo)
     * ---------------------------------- */
    const geoSelect = document.getElementById('geo-select');
    const addGeoBtn = document.getElementById('add-geo-sample-btn');
    const resetGeoBtn = document.getElementById('reset-geo-view-btn');
    const geoMapContainer = document.getElementById('geo-map-container');
    const geoSpinner = document.getElementById('geo-map-spinner');
    const geoPlaceholder = document.getElementById('geo-map-placeholder');

    // Só adiciona os listeners se os elementos da seção GEO existirem
    if (geoSelect) {
        /** ----------------------------------
         * Event Listeners (Geo)
         * ---------------------------------- */
        addGeoBtn.addEventListener('click', handleAddGeoSample);
        resetGeoBtn.addEventListener('click', handleResetGeoView);
    }

    /**
     * Manipula o clique no botão "Adicionar Rota" (Geo).
     * Carrega o arquivo JSON da amostra selecionada, armazena em cache,
     * e chama a função para renderizar o mapa da rota.
     */
    function handleAddGeoSample() {
        const selectedOption = geoSelect.options[geoSelect.selectedIndex];
        if (!selectedOption || !selectedOption.value) return;

        const jsonPath = selectedOption.value;
        const sampleName = selectedOption.textContent;

        if (loadedGeoData[jsonPath]) {
            alert("Esta rota já foi adicionada.");
            // Rola a tela até o mapa existente
            const mapId = `map-geo-${sampleName.replace(/[^a-zA-Z0.9]/g, '_')}`;
            const mapElement = document.getElementById(mapId);
            if (mapElement) {
                mapElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }

        geoPlaceholder.style.display = 'none';
        geoSpinner.classList.remove('d-none');
        geoSpinner.classList.add('d-flex');

        fetch(jsonPath)
            .then(response => {
                if (!response.ok) throw new Error(`Falha ao carregar ${jsonPath}`);
                return response.json();
            })
            .then(geoData => {
                // Armazena dados no cache
                loadedGeoData[jsonPath] = { name: sampleName, data: geoData };
                
                geoSpinner.classList.add('d-none');
                geoSpinner.classList.remove('d-flex');
                
                // Renderiza o mapa para esta rota
                renderGeoMap(jsonPath, sampleName, geoData);
            })
            .catch(err => {
                console.error("Erro ao carregar dados GEO:", err);
                geoSpinner.classList.add('d-none');
                geoMapContainer.innerHTML = `<div class="alert alert-danger">Falha ao carregar dados da amostra.</div>`;
            });
    }

    /**
     * Limpa a visualização de Geo.
     * Reseta caches, limpa os mapas e restaura o placeholder.
     */
    function handleResetGeoView() {
        loadedGeoData = {};
        // activeMaps é global, precisamos limpar apenas os mapas GEO
        // Vamos iterar e remover do cache global
        Object.keys(activeMaps).forEach(mapId => {
            if (mapId.startsWith('map-geo-')) {
                delete activeMaps[mapId];
            }
        });
        
        geoMapContainer.innerHTML = ''; // Limpa os mapas renderizados
        
        // Recoloca o placeholder dentro do contêiner de mapas
        geoMapContainer.appendChild(geoPlaceholder);
        geoPlaceholder.style.display = 'block';
        geoSelect.value = '';
    }

    /**
     * Renderiza um novo mapa Leaflet para a rota GPS.
     *
     * @param {string} jsonPath - O caminho para o JSON (ID do cache).
     * @param {string} sampleName - O nome da amostra (para o título).
     * @param {Object} geoData - Os dados GEO (formato: {'center': [...], 'path': [[...]]})
     */
    function renderGeoMap(jsonPath, sampleName, geoData) {
        const { center, path } = geoData;

        if (!path || path.length === 0) {
            alert(`Nenhum dado de rota encontrado para ${sampleName}.`);
            return;
        }

        // ID único para o mapa
        const mapId = `map-geo-${sampleName.replace(/[^a-zA-Z0.9]/g, '_')}`;

        // 1. Cria os contêineres do mapa (Wrapper e Div interna)
        const mapWrapper = document.createElement('div');
        mapWrapper.id = mapId;
        mapWrapper.className = 'col-12 col-lg-6 mb-4'; // Layout de bootstrap
        
        const title = document.createElement('h5');
        title.className = 'text-center';
        title.innerHTML = `Rota: ${sampleName}`;
        
        const mapInnerDiv = document.createElement('div');
        mapInnerDiv.className = 'leaflet-map-container'; // Usado para redimensionamento
        mapInnerDiv.setAttribute('data-map-id', mapId);  // Link para o cache 'activeMaps'

        mapWrapper.appendChild(title);
        mapWrapper.appendChild(mapInnerDiv);
        geoMapContainer.appendChild(mapWrapper);

        // 2. Criar o mapa Leaflet
        // Centraliza usando o ponto central calculado em Python
        const map = L.map(mapInnerDiv).setView(center, 16); // Zoom inicial

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxNativeZoom: 19,
            maxZoom: 22        
        }).addTo(map);

        // 3. Adicionar a Polilinha (a rota)
        const polyline = L.polyline(path, { color: 'red' }).addTo(map);

        // 4. Adicionar marcadores de Início e Fim
        L.marker(path[0]).addTo(map)
            .bindPopup('<b>Início da Rota</b>')
            .openPopup();
            
        L.marker(path[path.length - 1]).addTo(map)
            .bindPopup('<b>Fim da Rota</b>');

        // 5. Ajustar o zoom para caber a rota inteira
        map.fitBounds(polyline.getBounds(), { padding: [20, 20] });

        // 6. Salva a instância do mapa no cache global
        activeMaps[mapId] = map;

        // 7. Força o mapa a redimensionar
        setTimeout(() => map.invalidateSize(), 10);
    }

}); // Fim do 'DOMContentLoaded'