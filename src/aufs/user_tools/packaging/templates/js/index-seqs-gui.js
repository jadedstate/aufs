// Polyfill for Object.hasOwn
if (!Object.hasOwn) {
    Object.hasOwn = function (obj, prop) {
        return Object.prototype.hasOwnProperty.call(obj, prop);
    };
}

document.addEventListener('DOMContentLoaded', function () {
    let chartInstance = null;
    let gridApi = null;
    let gridOptions = null;
    let updatesPaused = false;
    const colorMap = {};  // To store colors for each series

    function fetchData() {
        if (updatesPaused) return;

        // Mock data for testing in browser
        const mockData = [
            {"FILENAME": "file1", "FRAMENUMBER": 1, "FILESIZE_MB": 2.5, "DOTEXTENSION": "txt", "TIMESEEN": 1627890123, "TIMELOGGED": 1627891123, "log_file": "log1.csv"},
            {"FILENAME": "file2", "FRAMENUMBER": 2, "FILESIZE_MB": 3.7, "DOTEXTENSION": "txt", "TIMESEEN": 1627890223, "TIMELOGGED": 1627891223, "log_file": "log2.csv"},
            // Add more mock data as needed
        ];

        const filteredData = mockData.filter(item => item.DOTEXTENSION !== 'tmp');

        if (gridApi && chartInstance) {
            updateGrid(filteredData);
            updateChart(gridApi.getDisplayedRowAtIndex.bind(gridApi));
        } else {
            initializeGrid(filteredData);
            initializeChart(filteredData);
        }
    }

    function initializeGrid(data) {
        const columnDefs = [
            { headerName: "FILENAME", field: "FILENAME", enableRowGroup: true,
                filter: 'agSetColumnFilter', sortable: true, sort: 'asc', sortIndex: 1,
                minWidth: 400
            },
            { headerName: "FRAME", field: "FRAMENUMBER", enableRowGroup: true,
                filter: 'agSetColumnFilter', sortable: true, sort: 'asc', sortIndex: 0,
                minWidth: 100
            },
            {
                headerName: "FILESIZE (MB)", field: "FILESIZE_MB", valueFormatter: (params) => {
                    return params.value !== undefined && params.value >= 0 ? params.value.toFixed(2) : '0';
                },
                enableRowGroup: true,
                filter: 'agSetColumnFilter'
            },
            { headerName: "DOTEXTENSION", field: "DOTEXTENSION" },
            { headerName: "TIMESEEN", field: "TIMESEEN" },
            { headerName: "TIMELOGGED", field: "TIMELOGGED" },
            { headerName: "log_file", field: "log_file" }
        ];

        gridOptions = {
            rowSelection: 'multiple',
            rowGroupPanelShow: "always",
            sideBar: {
                toolPanels: ['columns', 'filters'],
                position: 'right',
            },
            columnDefs: columnDefs,
            rowData: data,
            groupDisplayType: 'multipleColumns',
            getRowId: params => params.data.FRAMENUMBER,
            defaultColDef: {
                filter: true,
                floatingFilter: true,
                resizable: true,
                sortable: true
            },
            onSortChanged: function (params) {
                updateChart(params.api.getDisplayedRowAtIndex.bind(params.api));
            },
            onFilterChanged: function (params) {
                updateChart(params.api.getDisplayedRowAtIndex.bind(params.api));
            }
        };

        const eGridDiv = document.querySelector('#myGrid');
        gridApi = agGrid.createGrid(eGridDiv, gridOptions);
    }

    function initializeChart(data) {
        const groupedData = groupByFilenameAndExtension(data);
        const datasets = Object.keys(groupedData).map((key, index) => {
            if (!colorMap[key]) {
                colorMap[key] = getColor(index);
            }
            return {
                label: key,
                data: groupedData[key].map(item => ({ x: item.FRAMENUMBER, y: item.FILESIZE_MB })),
                backgroundColor: colorMap[key],
                borderColor: colorMap[key],
                borderWidth: 1,
                hidden: false // Ensure all datasets are visible by default
            };
        });

        const ctx = document.getElementById('myChart').getContext('2d');

        chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [...new Set(data.map(item => item.FRAMENUMBER))].sort((a, b) => a - b),
                datasets: datasets
            },
            options: {
                animation: false, // Disable animation
                scales: {
                    x: {
                        type: 'category',
                        title: { display: true, text: 'Frame' },
                        ticks: {
                            autoSkip: false
                        }
                    },
                    y: { title: { display: true, text: 'File Size (MB)' } }
                },
                plugins: {
                    legend: {
                        display: true,
                    }
                }
            }
        });
    }

    function updateGrid(data) {
        if (gridApi) {
            setTimeout(() => {
                const allRows = [];
                gridApi.forEachNode(node => allRows.push(node.data));
                gridApi.applyTransaction({ remove: allRows });  // Clear existing data
                gridApi.applyTransaction({ add: data });  // Add new data
            }, 0);
        }
    }

    function updateChart(displayedRowsFunction) {
        const rowCount = gridApi.getDisplayedRowCount();
        const displayedData = [];
        for (let i = 0; i < rowCount; i++) {
            const rowNode = displayedRowsFunction(i);
            displayedData.push(rowNode.data);
        }
        const groupedData = groupByFilenameAndExtension(displayedData);
        const datasets = Object.keys(groupedData).map((key, index) => {
            if (!colorMap[key]) {
                colorMap[key] = getColor(index);
            }
            return {
                label: key,
                data: groupedData[key].map(item => ({ x: item.FRAMENUMBER, y: item.FILESIZE_MB })),
                backgroundColor: colorMap[key],
                borderColor: colorMap[key],
                borderWidth: 1,
                hidden: false // Ensure all datasets are visible by default
            };
        });

        // Update the existing chart instance
        chartInstance.data.labels = [...new Set(displayedData.map(item => item.FRAMENUMBER))].sort((a, b) => a - b);
        chartInstance.data.datasets = datasets;
        chartInstance.update();
    }

    function groupByFilenameAndExtension(data) {
        return data.reduce((acc, item) => {
            const key = `${item.FILENAME}.${item.DOTEXTENSION}`;
            if (!acc[key]) {
                acc[key] = [];
            }
            acc[key].push(item);
            return acc;
        }, {});
    }

    function getColor(index) {
        const colors = [
            '#4bc0c0', '#36a201', '#ff6384',
            '#ffce56', '#9901ff', '#ff9f40',
            '#c7c7c7', '#0166ff', '#3cb371',
            '#ff69b4', '#7b6801', '#32cd32',
            '#ff69b4', '#01c8ee', '#32cd32',
            '#4bc0c0', '#36a2eb', '#ff6384',
            '#ffce56', '#9966ff', '#ff9f40',
            '#c7c7c7', '#5366ff', '#3cb371',
            '#ff69b4', '#7b68ee', '#32cd32',
            '#ff69b4', '#7bc8ee', '#32cd32',
            '#4bc0c0', '#3602b1', '#ff6384',
            '#ffce56', '#9949ff', '#ff9f40',
            '#c7c7c7', '#0166ff', '#3cb371',
            '#ff69b4', '#916801', '#32cd32',
            '#ff69b4', '#012fee', '#32cd32',
            '#4bc0c0', '#361010', '#ff6384',
            '#ffce56', '#9966ea', '#ff9f40',
            '#c7c7c7', '#53662b', '#3cb371',
            '#ff69b4', '#4068ee', '#32cd32',
            '#ff69b4', '#7bc8ee', '#32cd32'
        ];
        return colors[index % colors.length];
    }

    fetchData();
    setInterval(fetchData, 5000); // Fetch data every 5 seconds

    function updateButtonState() {
        if (updatesPaused) {
            toggleUpdatesButton.textContent = 'Resume Updates';
            toggleUpdatesButton.style.backgroundColor = '#aa0000';
        } else {
            toggleUpdatesButton.textContent = 'Pause Updates';
            toggleUpdatesButton.style.backgroundColor = '#0088aa';
        }
    }

    toggleUpdatesButton.addEventListener('click', function () {
        updatesPaused = !updatesPaused;
        updateButtonState();
        if (!updatesPaused) {
            fetchData();
        }
    });

    // Make the event listener passive
    document.addEventListener('touchstart', function () {}, { passive: true });
});
