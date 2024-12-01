import { AgCharts } from 'ag-charts-community';
import 'ag-charts-enterprise';

AgCharts.setLicenseKey("Using_this_{AG_Charts_and_AG_Grid}_Enterprise_key_{AG-063143}_in_excess_of_the_licence_granted_is_not_permitted___Please_report_misuse_to_legal@ag-grid.com___For_help_with_changing_this_key_please_contact_info@ag-grid.com___{Dasein_VFX_Ltd}_is_granted_a_{Single_Application}_Developer_License_for_the_application_{Opportunity_app.py}_only_for_{1}_Front-End_JavaScript_developer___All_Front-End_JavaScript_developers_working_on_{Opportunity_app.py}_need_to_be_licensed___{Opportunity_app.py}_has_not_been_granted_a_Deployment_License_Add-on___This_key_works_with_{AG_Charts_and_AG_Grid}_Enterprise_versions_released_before_{6_August_2025}____[v3]_[0102]_MTc1NDQzNDgwMDAwMA==d6878e1886072524d654527411c06681");

document.addEventListener('DOMContentLoaded', function () {
    const yAxisColor = '#999999';
    const xAxisColor = '#889999';
    const yGridLineColor = '#303030';
    const backgroundFillColor = '#171718';

    function createCustomChart(rowData) {
        const chartContainer = document.querySelector('#originalChartContainer');
        chartContainer.innerHTML = '';  // Clear previous chart

        // Preprocess the data to aggregate by Frames
        const aggregatedData = rowData.reduce((acc, row) => {
            const frame = row['Frames'];
            if (!acc[frame]) {
                acc[frame] = 0;
            }
            acc[frame] += row['RENDERTIME'];
            return acc;
        }, {});

        const data = Object.keys(aggregatedData).map(frame => ({
            Frames: frame,
            RENDERTIME: aggregatedData[frame]
        }));

        const chartOptions = {
            container: chartContainer,
            data: data,
            series: [{
                type: 'line',
                xKey: 'Frames',
                yKey: 'RENDERTIME',
                title: 'Aggregated Render Time',
            }],
            legend: {
                enabled: false
            },
            axes: [
                {
                    type: 'category',
                    position: 'bottom',
                    label: {
                        color: xAxisColor // Change this to your desired x-axis text color
                    },
                    line: {
                        color: xAxisColor // Change this to your desired x-axis text color
                    }
                },
                {
                    type: 'number',
                    position: 'left',
                    label: {
                        formatter: function (params) {
                            return typeof params.value === 'number' ? params.value.toFixed(0) : ''; // Ensure value is a number
                        },
                        color: yAxisColor // Change this to your desired y-axis text color
                    },
                    gridLine: {
                        style: [
                            {
                                stroke: yGridLineColor // Change this to your desired y-axis grid line color
                            }
                        ]
                    }
                }
            ],
            background: {
                fill: backgroundFillColor  // Change this to your desired background color
            },
            zoom: {
                enabled: true,
                enableSelecting: true,
                panKey: "shift",
            }
        };

        AgCharts.create(chartOptions);
    }

    // Function to create the original chart using the grid API
    function createOriginalChart(api) {
        api.addEventListener('firstDataRendered', function() {
            const rowData = [];
            api.forEachNode((node) => {
                rowData.push(node.data);
            });
            createCustomChart(rowData);
        });
    }

    function createLayerChart(api, rowData) {
        const chartContainer = document.querySelector('#layerChartContainer');
        chartContainer.innerHTML = '';  // Clear previous chart
    
        // Preprocess the data to group by LAYER and aggregate by Frames
        const groupedData = rowData.reduce((acc, row) => {
            const layer = row['DEADLINERENDERFULLNAME'];
            const frame = row['Frames'];
            if (!acc[layer]) {
                acc[layer] = {};
            }
            if (!acc[layer][frame]) {
                acc[layer][frame] = 0;
            }
            acc[layer][frame] += row['RENDERTIME'];
            return acc;
        }, {});
    
        // Calculate the overall aggregated data
        const aggregatedData = rowData.reduce((acc, row) => {
            const frame = row['Frames'];
            if (!acc[frame]) {
                acc[frame] = 0;
            }
            acc[frame] += row['RENDERTIME'];
            return acc;
        }, {});
    
        // Convert the grouped data into a series format for the chart
        const series = Object.keys(groupedData).map(layer => {
            return {
                xKey: 'Frames',
                yKey: 'RENDERTIME',
                title: layer,
                data: Object.keys(groupedData[layer]).map(frame => ({
                    Frames: frame,
                    RENDERTIME: groupedData[layer][frame]
                })),
                animation: {
                    enabled: true,
                    duration: 10000 // Animation duration in milliseconds
                }
            };
        });
    
        // Add the aggregated series to the chart
        series.push({
            xKey: 'Frames',
            yKey: 'RENDERTIME',
            title: 'Aggregated',
            data: Object.keys(aggregatedData).map(frame => ({
                Frames: frame,
                RENDERTIME: aggregatedData[frame]
            })),
            animation: {
                enabled: true,
                duration: 1000 // Animation duration in milliseconds
            }
        });
    
        const chartOptions = {
            container: chartContainer,
            data: [],
            series: series.map(s => ({
                type: 'line',
                xKey: s.xKey,
                yKey: s.yKey,
                title: s.title,
                data: s.data,
                animation: s.animation
            })),
            legend: {
                item: {
                    label: {
                        color: xAxisColor,
                    }
                },
                enabled: true,
                position: 'top'
            },
            axes: [
                {
                    type: 'category',
                    position: 'bottom',
                    label: {
                        color: xAxisColor // Change this to your desired x-axis text color
                    },
                    line: {
                        color: xAxisColor // Change this to your desired x-axis text color
                    }
                },
                {
                    type: 'number',
                    position: 'left',
                    label: {
                        formatter: function (params) {
                            return typeof params.value === 'number' ? params.value.toFixed(0) : ''; // Ensure value is a number
                        },
                        color: yAxisColor // Change this to your desired y-axis text color
                    },
                    gridLine: {
                        style: [
                            {
                                stroke: yGridLineColor // Change this to your desired y-axis grid line color
                            }
                        ]
                    }
                }
            ],
            background: {
                fill: backgroundFillColor  // Change this to your desired background color
            },
            zoom: {
                enabled: true,
                enableSelecting: true,
                panKey: "shift",
            }
        };
    
        AgCharts.create(chartOptions);
    }
    
    // Export the functions to be used in deadline-render-viewer-grid-default.js
    window.createOriginalChart = createOriginalChart;
    window.createLayerChart = createLayerChart;
});

document.addEventListener('DOMContentLoaded', function () {
    const yAxisColor = '#999999';
    const xAxisColor = '#889999';
    const yGridLineColor = '#303030';
    const backgroundFillColor = '#171718';

    function createCharts(api, directory) {
        const chartContainer = document.querySelector('#chart');
        chartContainer.innerHTML = '';  // Clear previous chart

        const rowData = [];
        api.forEachNode((node) => {
            rowData.push(node.data);
        });

        const chartOptions = {
            container: chartContainer,
            data: rowData,
            series: [{
                type: 'line',
                xKey: 'Frames',
                yKey: 'RENDERTIME',
                title: 'Aggregated Render Time',
            }],
            legend: {
                enabled: false
            },
            axes: [
                {
                    type: 'category',
                    position: 'bottom',
                    label: {
                        color: xAxisColor // Change this to your desired x-axis text color
                    },
                    line: {
                        color: xAxisColor // Change this to your desired x-axis text color
                    }
                },
                {
                    type: 'number',
                    position: 'left',
                    label: {
                        formatter: function (params) {
                            return typeof params.value === 'number' ? params.value.toFixed(0) : ''; // Ensure value is a number
                        },
                        color: yAxisColor // Change this to your desired y-axis text color
                    },
                    gridLine: {
                        style: [
                            {
                                stroke: yGridLineColor // Change this to your desired y-axis grid line color
                            }
                        ]
                    }
                }
            ],
            background: {
                fill: backgroundFillColor  // Change this to your desired background color
            },
            zoom: {
                enabled: true,
                enableSelecting: true,
                panKey: "shift",
            }
        };

        AgCharts.create(chartOptions);
    }

    window.createCharts = createCharts;
});
