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
            { headerName: "Instance ID", field: "InstanceId" },
            { headerName: "Instance Type", field: "InstanceType" },
            { headerName: "State", field: "State" },
            { headerName: "Public IP", field: "PublicIpAddress" },
            { headerName: "Private IP", field: "PrivateIpAddress" },
            { headerName: "Availability Zone", field: "AvailabilityZone" },
            { headerName: "Launch Time", field: "LaunchTime" },
            { headerName: "Key Name", field: "KeyName" },
            { headerName: "Lifecycle", field: "InstanceLifecycle" }
        ];
    
        const gridOptions = {
            columnDefs: columnDefs,
            rowData: data,
            defaultColDef: {
                filter: true,
                sortable: true,
                resizable: true,
                floatingFilter: true
            },
            enableRangeSelection: true,
            rowSelection: 'multiple',
            onGridReady: function(params) {
                params.api.sizeColumnsToFit();
            }
        };
    
        const eGridDiv = document.querySelector('#myGrid');
        gridApi = agGrid.createGrid(eGridDiv, gridOptions);
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

    document.addEventListener('DOMContentLoaded', function () {
        fetchData(); // Initialize the grid with instance data
        setInterval(fetchData, 5000); // Refresh data every 5 seconds
    });
    
    function fetchData() {
        new QWebChannel(qt.webChannelTransport, function(channel) {
            const dataProvider = channel.objects.dataProvider;
            dataProvider.getData().then(function(data) {
                initializeGrid(JSON.parse(data));
            });
        });
    }
    
 
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
