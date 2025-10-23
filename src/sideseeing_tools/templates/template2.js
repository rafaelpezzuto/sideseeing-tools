/**
 * =================================================================
 * FUNÇÃO DA SIDEBAR
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

    const plotlyCharts = activeSection.querySelectorAll('.plotly-chart');
    if (plotlyCharts.length > 0) {
        setTimeout(() => {
            plotlyCharts.forEach(chartDiv => {
                if (chartDiv.data) {
                    Plotly.Plots.resize(chartDiv);
                }
            });
        }, 150);
    }
}


/**
 * =================================================================
 * NOVA LÓGICA DE LAZY LOADING (AMOSTRA -> CHECKBOXES -> GRÁFICOS)
 * =================================================================
 */
document.addEventListener('DOMContentLoaded', function() {
    
    // Armazena os dados de TODAS as amostras selecionadas
    // Estrutura: { "path/to/json": { name: "Nome Amostra", data: [...] }, ... }
    let loadedSamplesData = {};

    // --- 1. Obter todos os elementos DOM ---
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

    if (!selectElement) return; // Se não houver seção de sensor, não faz nada

    // --- 2. Adicionar Event Listeners Principais ---

    // Listener para o botão "Adicionar"
    addSampleBtn.addEventListener('click', handleAddSampleClick);
    
    // Listener para o botão "Limpar Tudo"
    resetViewBtn.addEventListener('click', handleResetView);

    // Listener para cliques nos Checkboxes (usando delegação de evento)
    checkboxesList.addEventListener('change', handleCheckboxChange);

    // Listeners para botões "Marcar/Desmarcar Todos"
    checkAllBtn.addEventListener('click', () => toggleAllCheckboxes(true));
    uncheckAllBtn.addEventListener('click', () => toggleAllCheckboxes(false));


    // --- 3. Funções de Manipulação de Eventos ---

    /**
     * Disparado quando o usuário clica em "Adicionar"
     */
    function handleAddSampleClick() {
        const selectedOption = selectElement.options[selectElement.selectedIndex];
        if (!selectedOption || !selectedOption.value) return;

        const jsonPath = selectedOption.value;
        const sampleName = selectedOption.textContent;

        // Não recarrega se já foi carregado
        if (loadedSamplesData[jsonPath]) {
            alert("Esta amostra já foi adicionada.");
            return;
        }

        // Resetar a UI para o estado "carregando"
        placeholder.style.display = 'none';
        spinner.classList.remove('d-none');
        spinner.classList.add('d-flex');
        
        // Buscar os novos dados
        fetch(jsonPath)
            .then(response => {
                if (!response.ok) throw new Error(`Falha ao carregar ${jsonPath}`);
                return response.json();
            })
            .then(chartsData => {
                // Armazena os dados
                loadedSamplesData[jsonPath] = { name: sampleName, data: chartsData };
                
                // Esconde o spinner
                spinner.classList.add('d-none');
                spinner.classList.remove('d-flex');
                
                // Constrói a UI de checkboxes (APENAS para a nova amostra)
                populateSensorCheckboxes(jsonPath, sampleName, chartsData);
                
                // Mostra o container de checkboxes
                checkboxesContainer.style.display = 'block';

                // Renderiza os gráficos (com base nos checkboxes)
                renderSelectedCharts();
            })
            .catch(handleFetchError);
    }

    /**
     * Limpa toda a visualização, dados carregados e checkboxes
     */
    function handleResetView() {
        loadedSamplesData = {};
        chartsContainer.innerHTML = '';
        checkboxesList.innerHTML = '';
        checkboxesContainer.style.display = 'none';
        placeholder.style.display = 'block';
        selectElement.value = '';
    }


    /**
     * Disparado quando qualquer checkbox na lista é marcado/desmarcado
     */
    function handleCheckboxChange(event) {
        // Apenas re-renderiza se o clique foi em um checkbox de sensor
        if (event.target.classList.contains('sensor-toggle-checkbox')) {
            renderSelectedCharts();
        }
    }

    /**
     * ADICIONA checkboxes de uma nova amostra à lista
     */
    function populateSensorCheckboxes(jsonPath, sampleName, chartsData) {
        if (chartsData.length === 0) {
            checkboxesList.innerHTML += `<p class="text-muted">Nenhum sensor encontrado na amostra ${sampleName}.</p>`;
            return;
        }

        const sampleGroup = document.createElement('div');
        sampleGroup.className = 'sample-checkbox-group mb-2 p-2 border rounded';
        
        let groupHTML = `<strong class="d-block mb-2">${sampleName}</strong>`;

        chartsData.forEach((chart, index) => {
            // Título limpo (ex: "acelerometro")
            const title = chart.layout.title ? chart.layout.title.replace(/<b>Sensor:<\/b>\s*/i, '') : `Sensor ${index + 1}`;
            const chartId = chart.chart_id;

            groupHTML += `
                <div class="form-check form-check-inline">
                    <input class="form-check-input sensor-toggle-checkbox" 
                           type="checkbox" 
                           value="${chartId}" 
                           id="chk-${chartId}"
                           data-sample-path="${jsonPath}"
                           data-sensor-name="${title}"> 
                    <label class="form-check-label" for="chk-${chartId}">
                        ${title}
                    </label>
                </div>
            `;
        });

        sampleGroup.innerHTML = groupHTML;
        checkboxesList.appendChild(sampleGroup);
    }

    /**
     * =================================================================
     * FUNÇÃO ATUALIZADA (LÓGICA CORRETA)
     * =================================================================
     * Desenha um gráfico para CADA checkbox selecionado, sem agrupar.
     * Adiciona o nome da amostra ao TÍTULO do gráfico.
     */
    function renderSelectedCharts() {
        chartsContainer.innerHTML = ''; // Limpa gráficos antigos

        // Pega todos os checkboxes que estão MARCADOS
        const checkedBoxes = checkboxesList.querySelectorAll('.sensor-toggle-checkbox:checked');

        if (checkedBoxes.length === 0) {
            chartsContainer.innerHTML = '<p class="text-center text-muted fs-5">Nenhum sensor selecionado para exibição.</p>';
            return;
        }

        // Itera sobre CADA checkbox marcado individualmente
        checkedBoxes.forEach(checkbox => {
            const chartId = checkbox.value;
            const samplePath = checkbox.dataset.samplePath; 

            // 1. Encontra os dados da amostra correta
            const sample = loadedSamplesData[samplePath];
            if (!sample) return; 

            // 2. Encontra os dados do gráfico específico dentro da amostra
            const chartData = sample.data.find(c => c.chart_id === chartId);

            if (chartData) {
                // 3. Prepara o DIV
                const chartDiv = document.createElement('div');
                // Usamos o chartId original, que é único por amostra/sensor
                chartDiv.id = chartData.chart_id; 
                chartDiv.className = 'col-12 col-lg-6 mb-4'; // Ocupa metade da tela
                chartDiv.style.width = '100%';
                chartDiv.style.height = '450px';
                
                chartsContainer.appendChild(chartDiv);

                // 4. Prepara o Layout (Adicionando subtítulo)
                const newLayout = { ...chartData.layout }; // Copia layout original
                const originalTitle = newLayout.title || 'Sensor';
                const sampleName = sample.name;

                // Adiciona o nome da amostra como subtítulo
                newLayout.title = `${originalTitle}<br><span style="font-size:0.8em; color: #555;">Amostra: ${sampleName}</span>`;

                // 5. Plota o gráfico
                // Usa chartData.data (os traces originais "x", "y", "z")
                // A legenda ficará limpa, como pedido.
                Plotly.newPlot(chartDiv, chartData.data, newLayout, { responsive: true });
            }
        });
    }

    /**
     * Marca ou desmarca todos os checkboxes e re-renderiza
     */
    function toggleAllCheckboxes(checkedState) {
        const checkboxes = checkboxesList.querySelectorAll('.sensor-toggle-checkbox');
        checkboxes.forEach(chk => {
            chk.checked = checkedState;
        });
        renderSelectedCharts();
    }

    /**
     * Função para tratar erros do fetch
     */
    function handleFetchError(error) {
        console.error('Erro ao carregar dados do sensor:', error);
        spinner.classList.add('d-none');
        spinner.classList.remove('d-flex');
        chartsContainer.innerHTML = `<div class="alert alert-danger">Falha ao carregar dados da amostra.</div>`;
    }

});