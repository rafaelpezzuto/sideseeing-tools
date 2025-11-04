/**
 * =================================================================
 * ARQUIVO: template2.js
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
    const plotlyLayout = (title) => ({
        title: title || '',
        margin: { l: 50, r: 20, b: 100, t: 40 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        legend: { orientation: 'h', y: -0.3 }
    });

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
    const wifiControlsContainer = document.getElementById('wifi-controls-container');
    const wifiControlsList = document.getElementById('wifi-controls-list');
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

        // Delegação de eventos para os controles de Wi-Fi:
        // Um único listener 'click' trata os botões "Plotar", "Mostrar Todos" e "Esconder Todos".
        wifiControlsList.addEventListener('click', handleWifiGlobalClick);
        
        // Um único listener 'keyup' trata todas as barras de pesquisa.
        wifiControlsList.addEventListener('keyup', handleWifiSearch);
    }

    /**
     * Manipulador de clique global (delegação de evento) para a lista de controles Wi-Fi.
     * Identifica qual tipo de botão foi clicado e chama a função correspondente.
     * @param {Event} event O objeto do evento 'click'.
     */
    function handleWifiGlobalClick(event) {
        const target = event.target;

        // Se clicou no botão "Plotar [banda]"
        if (target.classList.contains('plot-wifi-btn')) {
            handleWifiControlClick(target);
        }
        // Se clicou no botão "Mostrar Todos"
        else if (target.classList.contains('wifi-show-all-btn')) {
            handleShowAllWifi(target);
        }
        // Se clicou no botão "Esconder Todos"
        else if (target.classList.contains('wifi-hide-all-btn')) {
            handleHideAllWifi(target);
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
        // Busca o 'sampleGroup' pai para encontrar a barra de pesquisa
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
     * 1. Se a pesquisa estiver vazia, esconde TODOS os itens.
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

            // Lógica de filtragem:
            if (filterText === "") {
                // 1. Se a barra de pesquisa estiver vazia, esconde o item
                item.style.display = 'none';
            }
            else if (ssidName.includes(filterText)) {
                // 2. Se não estiver vazia E der match, mostra
                item.style.display = 'block';
            }
            else {
                // 3. Se não der match, esconde
                item.style.display = 'none';
            }
        });
    }

    /**
     * Manipula o clique no botão "Adicionar Amostra" (Wi-Fi).
     * Carrega o arquivo JSON da amostra selecionada, armazena em cache,
     * e chama a função para popular os controles (botões, pesquisa, etc).
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
                // Armazena dados no cache
                loadedWifiData[jsonPath] = { name: sampleName, data: wifiData };
                
                wifiSpinner.classList.add('d-none');
                wifiSpinner.classList.remove('d-flex');
                
                // Cria a UI de controles (pesquisa, botões) para esta amostra
                populateWifiControls(jsonPath, sampleName, wifiData);
                
                wifiControlsContainer.style.display = 'block';
            })
            .catch(err => {
                console.error("Erro ao carregar dados Wi-Fi:", err);
                wifiSpinner.classList.add('d-none');
                wifiMapContainer.innerHTML = `<div class="alert alert-danger">Falha ao carregar dados da amostra.</div>`;
            });
    }

    /**
     * Limpa a visualização de Wi-Fi.
     * Reseta caches, limpa os mapas e controles, e restaura o placeholder.
     */
    function handleResetWifiView() {
        loadedWifiData = {};
        activeMaps = {}; // Limpa o cache de mapas Leaflet
        wifiControlsList.innerHTML = '';
        wifiMapContainer.innerHTML = ''; // Limpa os mapas renderizados
        wifiControlsContainer.style.display = 'none';
        
        // Recoloca o placeholder dentro do contêiner de mapas
        wifiMapContainer.appendChild(wifiPlaceholder);
        wifiPlaceholder.style.display = 'block';
        wifiSelect.value = '';
    }

    /**
     * Cria a UI de controle para uma amostra de Wi-Fi recém-carregada.
     * Isso inclui: Título da amostra, Barra de Pesquisa, Botões "Mostrar/Esconder Todos",
     * e a lista (grid) de botões de plotagem para cada SSID/banda.
     *
     * @param {string} jsonPath - O caminho para o JSON (ID do cache).
     * @param {string} sampleName - O nome da amostra (para o título).
     * @param {Object} wifiData - Os dados de Wi-Fi (formato: {'SSID': {'Banda': [[...]]}})
     */
    function populateWifiControls(jsonPath, sampleName, wifiData) {
        const ssids = Object.keys(wifiData);
        
        const sampleGroup = document.createElement('div');
        sampleGroup.className = 'sample-wifi-group mb-3 p-2 border rounded';
        
        // ID único para a *lista* de SSIDs desta amostra (para a pesquisa)
        const listId = `wifi-list-${sampleName.replace(/[^a-zA-Z0.9]/g, '_')}`;

        let groupHTML = `<strong class="d-block mb-2">${sampleName}</strong>`;
        
        // 1. Adiciona a barra de pesquisa
        groupHTML += `
            <input type="text" 
                   class="form-control form-control-sm mb-2 wifi-search-bar" 
                   placeholder="Digite para filtrar SSIDs..."
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
        groupHTML += `<div id="${listId}" class="wifi-ssid-list-grid" style="max-height: 250px; overflow-y: auto;">`;

        if (ssids.length === 0) {
            groupHTML += `<p class="text-muted">Nenhum SSID encontrado na amostra ${sampleName}.</p>`;
        } else {
            ssids.sort().forEach(ssid => {
                const bands = Object.keys(wifiData[ssid]);
                
                // 4. Contêiner para os botões de um SSID
                // Começa escondido (display: none)
                groupHTML += `<div class="mb-2 wifi-ssid-item" data-ssid-name="${ssid.toLowerCase()}" style="display: none;">
                                <span class="fw-bold">${ssid}</span>: `;
                
                // 5. Cria os botões de plotagem (ex: "Plotar 2.4GHz")
                bands.forEach(band => {
                    // ID único para o mapa que será gerado
                    const mapId = `map-${sampleName.replace(/[^a-zA-Z0.9]/g, '_')}-${ssid.replace(/[^a-zA-Z0.9]/g, '_')}-${band}`;
                    
                    groupHTML += `
                        <button class="btn btn-sm btn-outline-primary plot-wifi-btn"
                                data-json-path="${jsonPath}"
                                data-ssid="${ssid}"
                                data-band="${band}"
                                data-map-id="${mapId}">
                            Plotar ${band}
                        </button>
                    `;
                });
                groupHTML += `</div>`; // Fim de wifi-ssid-item
            });
        }
        
        groupHTML += `</div>`; // Fim da div da lista (grid)
        
        sampleGroup.innerHTML = groupHTML;
        wifiControlsList.appendChild(sampleGroup);
    }

    /**
     * Manipula o clique em um botão "Plotar [banda]".
     * Esta função é chamada pela delegação de evento `handleWifiGlobalClick`.
     * Cria e renderiza um novo mapa de calor Leaflet.
     *
     * @param {HTMLElement} button O botão "plot-wifi-btn" que foi clicado.
     */
    function handleWifiControlClick(button) {
        // Pega os dados armazenados no botão
        const { jsonPath, ssid, band, mapId } = button.dataset;

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
        const mapWrapper = document.createElement('div');
        mapWrapper.id = mapId;
        mapWrapper.className = 'col-12 col-lg-6 mb-4'; // Layout de bootstrap
        
        const title = document.createElement('h5');
        title.className = 'text-center';
        title.innerHTML = `${ssid} (${band})<br><span style="font-size:0.8em; color: #555;">Amostra: ${sampleData.name}</span>`;
        
        const mapInnerDiv = document.createElement('div');
        mapInnerDiv.className = 'leaflet-map-container'; // Usado para redimensionamento
        mapInnerDiv.setAttribute('data-map-id', mapId);  // Link para o cache 'activeMaps'

        mapWrapper.appendChild(title);
        mapWrapper.appendChild(mapInnerDiv);
        wifiMapContainer.appendChild(mapWrapper);

        // 3. Lógica de Plotagem (recriando a lógica do notebook)
        
        // 3a. Calcular centro e normalizar dados
        let centerLat = 0;
        let centerLon = 0;
        const levels = heatData.map(p => p[2]); // Todos os níveis de sinal (ex: -90, -50)
        const minLevel = Math.min(...levels);   // Sinal mais fraco (ex: -90)
        const maxLevel = Math.max(...levels);   // Sinal mais forte (ex: -50)
        const range = maxLevel - minLevel;      // Amplitude do sinal (ex: 40)

        const normalizedHeatData = heatData.map(point => {
            const [lat, lon, level] = point;
            centerLat += lat;
            centerLon += lon;
            
            // Normaliza a intensidade (level) de 0.0 a 1.0
            // O plugin Leaflet.heat espera 'intensity' entre 0.0 (frio) e 1.0 (quente)
            let intensity = 0.5; // Caso padrão se houver só 1 ponto (range=0)
            if (range > 0) {
                // (level - min) / range -> ex: (-50 - (-90)) / 40 = 40 / 40 = 1.0 (quente)
                // ex: (-90 - (-90)) / 40 = 0 / 40 = 0.0 (frio)
                intensity = (level - minLevel) / range;
            }
            return [lat, lon, intensity]; // Retorna [lat, lon, intensity_normalizada]
        });
        
        // Calcula a média para centralizar o mapa
        centerLat /= heatData.length;
        centerLon /= heatData.length;

        // 3b. Criar o mapa Leaflet
        const map = L.map(mapInnerDiv).setView([centerLat, centerLon], 18); // Zoom inicial 18

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxNativeZoom: 19, // Zoom máximo dos tiles do provedor
            maxZoom: 22        // Permite "over-zoom" (zoom digital)
        }).addTo(map);

        // 3c. Adicionar a camada de HeatMap
        L.heatLayer(normalizedHeatData, {
            radius: 15, // Raio de influência de cada ponto
            blur: 10,   // Nível de "borrão"
        }).addTo(map);

        // 4. Salva a instância do mapa no cache global
        activeMaps[mapId] = map;

        // 5. Força o mapa a redimensionar
        // Necessário pois o mapa foi criado em uma div que não estava visível
        // ou que mudou de tamanho.
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