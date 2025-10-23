/**
 * =================================================================
 * FUNÇÃO DA SIDEBAR (INTOCADA)
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
    
    // Armazena os dados da amostra selecionada
    let currentSampleData = [];

    // --- 1. Obter todos os elementos DOM ---
    const selectElement = document.getElementById('sensor-select');
    const chartsContainer = document.getElementById('charts-container');
    const spinner = document.getElementById('charts-spinner');
    const placeholder = document.getElementById('charts-placeholder');
    const checkboxesContainer = document.getElementById('sensor-checkboxes-container');
    const checkboxesList = document.getElementById('sensor-checkboxes-list');
    const checkAllBtn = document.getElementById('check-all-sensors');
    const uncheckAllBtn = document.getElementById('uncheck-all-sensors');

    if (!selectElement) return; // Se não houver seção de sensor, não faz nada

    // --- 2. Adicionar Event Listeners Principais ---

    // Listener para o <select> de Amostras
    selectElement.addEventListener('change', handleSampleSelectChange);
    
    // Listener para cliques nos Checkboxes (usando delegação de evento)
    checkboxesList.addEventListener('change', handleCheckboxChange);

    // Listeners para botões "Marcar/Desmarcar Todos"
    checkAllBtn.addEventListener('click', () => toggleAllCheckboxes(true));
    uncheckAllBtn.addEventListener('click', () => toggleAllCheckboxes(false));


    // --- 3. Funções de Manipulação de Eventos ---

    /**
     * Disparado quando o usuário seleciona uma nova Amostra no <select>
     */
    function handleSampleSelectChange() {
        const jsonPath = selectElement.value;
        if (!jsonPath) return;

        // Resetar a UI para o estado "carregando"
        chartsContainer.innerHTML = '';
        checkboxesList.innerHTML = '';
        checkboxesContainer.style.display = 'none';
        placeholder.style.display = 'none';
        spinner.classList.remove('d-none');
        spinner.classList.add('d-flex');
        
        // Limpar dados antigos
        currentSampleData = [];

        // Buscar os novos dados
        fetch(jsonPath)
            .then(response => {
                if (!response.ok) throw new Error(`Falha ao carregar ${jsonPath}`);
                return response.json();
            })
            .then(chartsData => {
                // Armazena os dados (ex: 15 sensores) globalmente
                currentSampleData = chartsData;
                
                // Esconde o spinner
                spinner.classList.add('d-none');
                spinner.classList.remove('d-flex');
                
                // Constrói a UI de checkboxes
                populateSensorCheckboxes(chartsData);
                
                // Mostra o container de checkboxes
                checkboxesContainer.style.display = 'block';

                // Renderiza os gráficos (com base nos checkboxes, que por padrão estão marcados)
                renderSelectedCharts();
            })
            .catch(handleFetchError);
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
     * Preenche a <div> com os checkboxes dos sensores encontrados
     */
    function populateSensorCheckboxes(chartsData) {
        checkboxesList.innerHTML = ''; // Limpa checkboxes antigos
        
        if (chartsData.length === 0) {
            checkboxesList.innerHTML = '<p class="text-muted">Nenhum sensor encontrado nesta amostra.</p>';
            return;
        }

        chartsData.forEach((chart, index) => {
            // Tenta extrair um nome limpo do título (ex: "<b>Sensor:</b> acelerometro")
            const title = chart.layout.title ? chart.layout.title.replace(/<b>Sensor:<\/b>\s*/i, '') : `Sensor ${index + 1}`;
            const chartId = chart.chart_id;

            const div = document.createElement('div');
            div.className = 'form-check';
            div.innerHTML = `
                <input class="form-check-input sensor-toggle-checkbox" type="checkbox" value="${chartId}" id="chk-${chartId}">
                <label class="form-check-label" for="chk-${chartId}">
                    ${title}
                </label>
            `;
            checkboxesList.appendChild(div);
        });
    }

    /**
     * Desenha os gráficos no container com base nos checkboxes marcados
     */
    function renderSelectedCharts() {
        chartsContainer.innerHTML = ''; // Limpa gráficos antigos

        // Pega todos os checkboxes que estão MARCADOS
        const checkedBoxes = checkboxesList.querySelectorAll('.sensor-toggle-checkbox:checked');

        if (checkedBoxes.length === 0) {
            chartsContainer.innerHTML = '<p class="text-center text-muted fs-5">Nenhum sensor selecionado para exibição.</p>';
            return;
        }

        // Itera apenas sobre os selecionados
        checkedBoxes.forEach(checkbox => {
            const chartId = checkbox.value;
            
            // Encontra os dados completos para este chartId
            const chartData = currentSampleData.find(c => c.chart_id === chartId);

            if (chartData) {
                const chartDiv = document.createElement('div');
                chartDiv.id = chartData.chart_id;
                chartDiv.className = 'col-12 col-lg-6 mb-4'; // Ocupa metade da tela em desktops
                chartDiv.style.width = '100%';
                chartDiv.style.height = '450px';
                
                chartsContainer.appendChild(chartDiv);

                // Plota o gráfico
                Plotly.newPlot(chartDiv, chartData.data, chartData.layout, { responsive: true });
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
        // Após mudar, re-renderiza os gráficos
        renderSelectedCharts();
    }

    /**
     * Função para tratar erros do fetch
     */
    function handleFetchError(error) {
        console.error('Erro ao carregar dados do sensor:', error);
        spinner.classList.add('d-none');
        spinner.classList.remove('d-flex');
        // Mostra o erro no container de gráficos
        chartsContainer.innerHTML = `<div class="alert alert-danger">Falha ao carregar dados da amostra.</div>`;
    }

});