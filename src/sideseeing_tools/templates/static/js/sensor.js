function initSensorSection(loadedSamplesData) {
    const sensorSampleSelect = document.getElementById('sensor-select');
    const sensorTypeSelect = document.getElementById('sensor-type-select');
    const chartsContainer = document.getElementById('charts-container');
    const spinner = document.getElementById('charts-spinner');
    const placeholder = document.getElementById('charts-placeholder');

    if (!sensorSampleSelect) return;

    sensorSampleSelect.addEventListener('change', handleSensorSampleChange);
    if (sensorTypeSelect) {
        sensorTypeSelect.addEventListener('change', handleSensorTypeChange);
    }

    function handleSensorSampleChange() {
        const selectedOption = sensorSampleSelect.options[sensorSampleSelect.selectedIndex];
        if (!selectedOption || !selectedOption.value) return;

        const jsonPath = selectedOption.value;
        const sampleName = selectedOption.textContent;

        if (loadedSamplesData[jsonPath]) {
            populateSensorTypeSelect(jsonPath, sampleName, loadedSamplesData[jsonPath].data);
            return;
        }

        if (placeholder) placeholder.style.display = 'none';
        if (spinner) spinner.classList.remove('hidden');
        if (spinner) spinner.classList.add('flex');

        fetch(jsonPath)
            .then(response => {
                if (!response.ok) throw new Error(`Failed to load ${jsonPath}`);
                return response.json();
            })
            .then(chartsData => {
                loadedSamplesData[jsonPath] = { name: sampleName, data: chartsData };
                
                if (spinner) spinner.classList.add('hidden');
                if (spinner) spinner.classList.remove('flex');
                
                populateSensorTypeSelect(jsonPath, sampleName, chartsData);
            })
            .catch(handleFetchError);
    }

    function handleSensorTypeChange() {
        const selectedOption = sensorTypeSelect.options[sensorTypeSelect.selectedIndex];
        if (!selectedOption || !selectedOption.value) {
            chartsContainer.innerHTML = '';
            if (placeholder) chartsContainer.appendChild(placeholder);
            if (placeholder) placeholder.style.display = 'flex';
            return;
        }

        const { samplePath, chartId } = selectedOption.dataset;
        renderSensorChart(samplePath, chartId);
    }

    function populateSensorTypeSelect(jsonPath, sampleName, chartsData) {
        if (!sensorTypeSelect) return;

        sensorTypeSelect.innerHTML = '<option selected disabled value="">-- Choose a sensor to view --</option>';
        
        chartsData.forEach((chart, index) => {
            const title = chart.layout.title ? chart.layout.title.replace(/<b>Sensor:<\/b>\s*/i, '') : `Sensor ${index + 1}`;
            const chartId = chart.chart_id;
            const option = document.createElement('option');
            option.value = chartId;
            option.textContent = title;
            option.dataset.samplePath = jsonPath;
            option.dataset.chartId = chartId;
            sensorTypeSelect.appendChild(option);
        });

        sensorTypeSelect.disabled = false;
        handleSensorTypeChange();
    }

    function renderSensorChart(samplePath, chartId) {
        chartsContainer.innerHTML = '';
        if (placeholder) placeholder.style.display = 'none';

        const sample = loadedSamplesData[samplePath];
        if (!sample) return;

        const chartData = sample.data.find(c => c.chart_id === chartId);
        if (chartData) {
            const chartDiv = document.createElement('div');
            chartDiv.id = chartData.chart_id;
            chartDiv.className = 'w-full h-full plotly-chart';
            chartsContainer.appendChild(chartDiv);
            
            const newLayout = JSON.parse(JSON.stringify(chartData.layout));
            const originalTitle = newLayout.title || 'Sensor';
            const sampleName = sample.name;

            newLayout.title = `${originalTitle}<br><span style="font-size:0.8em; color: #555;">Sample: ${sampleName}</span>`;

            Plotly.newPlot(chartDiv, chartData.data, newLayout, { 
                responsive: true, 
                useResizeHandler: true,
            });
        }
    }

    function handleFetchError(error) {
        console.error('Error loading sensor data:', error);
        if (spinner) spinner.classList.add('hidden');
        if (spinner) spinner.classList.remove('flex');
        chartsContainer.innerHTML = `<div class="p-4 text-red-600 font-medium">Failed to load sample data. See console for details.</div>`;
    }
}
