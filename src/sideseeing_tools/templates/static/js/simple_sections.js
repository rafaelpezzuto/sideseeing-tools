function initializeSimpleSection(sectionPrefix) {
    const select = document.getElementById(`${sectionPrefix}-select`);
    const container = document.getElementById(`${sectionPrefix}-container`);
    const spinner = document.getElementById(`${sectionPrefix}-spinner`);
    const placeholder = document.getElementById(`${sectionPrefix}-placeholder`);
    
    let loadedData = {};

    if (!select || !container || !spinner || !placeholder) {
        return;
    }

    select.addEventListener('change', handleSelectionChange);

    function handleSelectionChange() {
        const selectedOption = select.options[select.selectedIndex];
        if (!selectedOption || !selectedOption.value) {
            resetView();
            return;
        }

        const jsonPath = selectedOption.value;
        const sampleName = selectedOption.textContent;

        resetView(false);

        placeholder.style.display = 'none';
        spinner.classList.remove('hidden');
        spinner.classList.add('flex');

        if (loadedData[jsonPath]) {
            renderContent(loadedData[jsonPath].data, sampleName);
            spinner.classList.add('hidden');
            spinner.classList.remove('flex');
            return;
        }

        fetch(jsonPath)
            .then(response => {
                if (!response.ok) throw new Error(`Failed to load ${jsonPath}`);
                return response.json();
            })
            .then(data => {
                loadedData[jsonPath] = { name: sampleName, data: data };
                spinner.classList.add('hidden');
                spinner.classList.remove('flex');
                renderContent(data, sampleName);
            })
            .catch(err => {
                console.error(`Error loading ${sectionPrefix} data:`, err);
                spinner.classList.add('hidden');
                container.innerHTML = `<div class="p-4 text-red-600 font-medium">Failed to load sample data. See console for details.</div>`;
            });
    }

    function renderContent(data, sampleName) {
        container.innerHTML = `
            <div class="p-4">
                <h4 class="font-semibold">${sampleName}</h4>
                <pre class="bg-gray-100 p-3 rounded-md mt-2 text-xs overflow-auto">${JSON.stringify(data, null, 2)}</pre>
            </div>
        `;
    }

    function resetView(resetSelect = true) {
        container.innerHTML = '';
        container.appendChild(placeholder);
        placeholder.style.display = 'flex';
        if (resetSelect) {
            select.value = '';
        }
    }
}
