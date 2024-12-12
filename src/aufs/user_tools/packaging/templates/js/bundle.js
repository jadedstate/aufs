/*
 * ATTENTION: The "eval" devtool has been used (maybe by default in mode: "development").
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ "./src/rendering_utils/resources/js/initAgCharts.js":
/*!******************************************************!*\
  !*** ./src/rendering_utils/resources/js/initAgCharts.js ***!
  \******************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var ag_charts_community__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ag-charts-community */ \"./node_modules/ag-charts-community/dist/package/main.esm.mjs\");\n/* harmony import */ var ag_charts_enterprise__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ag-charts-enterprise */ \"./node_modules/ag-charts-enterprise/dist/package/main.esm.mjs\");\n\n\nag_charts_community__WEBPACK_IMPORTED_MODULE_0__.AgCharts.setLicenseKey(\"Using_this_{AG_Charts_and_AG_Grid}_Enterprise_key_{AG-063143}_in_excess_of_the_licence_granted_is_not_permitted___Please_report_misuse_to_legal@ag-grid.com___For_help_with_changing_this_key_please_contact_info@ag-grid.com___{Dasein_VFX_Ltd}_is_granted_a_{Single_Application}_Developer_License_for_the_application_{Opportunity_app.py}_only_for_{1}_Front-End_JavaScript_developer___All_Front-End_JavaScript_developers_working_on_{Opportunity_app.py}_need_to_be_licensed___{Opportunity_app.py}_has_not_been_granted_a_Deployment_License_Add-on___This_key_works_with_{AG_Charts_and_AG_Grid}_Enterprise_versions_released_before_{6_August_2025}____[v3]_[0102]_MTc1NDQzNDgwMDAwMA==d6878e1886072524d654527411c06681\");\ndocument.addEventListener('DOMContentLoaded', function () {\n  var yAxisColor = '#999999';\n  var xAxisColor = '#889999';\n  var yGridLineColor = '#303030';\n  var backgroundFillColor = '#171718';\n  function createOriginalChart(api) {\n    var createRangeChartParams = {\n      cellRange: {\n        columns: ['Frames', 'RENDERTIME']\n      },\n      chartType: 'line',\n      chartContainer: document.querySelector('#originalChartContainer'),\n      aggFunc: 'sum',\n      chartThemeOverrides: {\n        common: {\n          background: {\n            fill: backgroundFillColor // light/mid grey\n          },\n          legend: {\n            enabled: false,\n            position: 'top'\n          },\n          axes: {\n            number: {\n              label: {\n                formatter: function formatter(params) {\n                  return typeof params.value === 'number' ? params.value.toFixed(0) : ''; // Ensure value is a number\n                },\n                color: yAxisColor // Change this to your desired y-axis text color\n              },\n              gridLine: {\n                style: [{\n                  stroke: yGridLineColor // Change this to your desired y-axis grid line color\n                }]\n              }\n            },\n            category: {\n              label: {\n                color: xAxisColor // Change this to your desired x-axis text color\n              },\n              line: {\n                stroke: xAxisColor // Change this to your desired x-axis text color\n              }\n            }\n          }\n        }\n      }\n    };\n    api.createRangeChart(createRangeChartParams);\n  }\n  function createLayerChart(api, rowData) {\n    var chartContainer = document.querySelector('#layerChartContainer');\n    chartContainer.innerHTML = ''; // Clear previous chart\n\n    // Preprocess the data to group by LAYER and aggregate by Frames\n    var groupedData = rowData.reduce(function (acc, row) {\n      var layer = row['DEADLINERENDERFULLNAME'];\n      var frame = row['Frames'];\n      if (!acc[layer]) {\n        acc[layer] = {};\n      }\n      if (!acc[layer][frame]) {\n        acc[layer][frame] = 0;\n      }\n      acc[layer][frame] += row['RENDERTIME'];\n      return acc;\n    }, {});\n\n    // Calculate the overall aggregated data\n    var aggregatedData = rowData.reduce(function (acc, row) {\n      var frame = row['Frames'];\n      if (!acc[frame]) {\n        acc[frame] = 0;\n      }\n      acc[frame] += row['RENDERTIME'];\n      return acc;\n    }, {});\n\n    // Convert the grouped data into a series format for the chart\n    var series = Object.keys(groupedData).map(function (layer) {\n      return {\n        xKey: 'Frames',\n        yKey: 'RENDERTIME',\n        title: layer,\n        data: Object.keys(groupedData[layer]).map(function (frame) {\n          return {\n            Frames: frame,\n            RENDERTIME: groupedData[layer][frame]\n          };\n        })\n      };\n    });\n\n    // Add the aggregated series to the chart\n    series.push({\n      xKey: 'Frames',\n      yKey: 'RENDERTIME',\n      title: 'Aggregated',\n      data: Object.keys(aggregatedData).map(function (frame) {\n        return {\n          Frames: frame,\n          RENDERTIME: aggregatedData[frame]\n        };\n      })\n    });\n    var chartOptions = {\n      container: chartContainer,\n      data: [],\n      series: series.map(function (s) {\n        return {\n          type: 'line',\n          xKey: s.xKey,\n          yKey: s.yKey,\n          title: s.title,\n          data: s.data\n        };\n      }),\n      legend: {\n        item: {\n          label: {\n            color: xAxisColor\n          }\n        },\n        enabled: true,\n        position: 'top'\n      },\n      axes: [{\n        type: 'category',\n        position: 'bottom',\n        label: {\n          color: xAxisColor // Change this to your desired x-axis text color\n        },\n        line: {\n          color: xAxisColor // Change this to your desired x-axis text color\n        }\n      }, {\n        type: 'number',\n        position: 'left',\n        label: {\n          formatter: function formatter(params) {\n            return typeof params.value === 'number' ? params.value.toFixed(0) : ''; // Ensure value is a number\n          },\n          color: yAxisColor // Change this to your desired y-axis text color\n        },\n        gridLine: {\n          style: [{\n            stroke: yGridLineColor // Change this to your desired y-axis grid line color\n            // lineDash: [4, 2]\n          }]\n        }\n      }],\n      background: {\n        fill: backgroundFillColor // Change this to your desired background color\n      },\n      zoom: {\n        enabled: true,\n        enableSelecting: true,\n        panKey: \"shift\"\n      }\n    };\n    ag_charts_community__WEBPACK_IMPORTED_MODULE_0__.AgCharts.create(chartOptions);\n  }\n\n  // Export the functions to be used in deadline-render-viewer-grid-default.js\n  window.createOriginalChart = createOriginalChart;\n  window.createLayerChart = createLayerChart;\n});\n\n//# sourceURL=webpack://utils/./src/rendering_utils/resources/js/initAgCharts.js?");

/***/ }),

/***/ "./node_modules/ag-charts-community/dist/package/main.esm.mjs":
/*!********************************************************************!*\
  !*** ./node_modules/ag-charts-community/dist/package/main.esm.mjs ***!
  \********************************************************************/
/***/ ((__unused_webpack___webpack_module__, __webpack_exports__, __webpack_require__) => {


/***/ }),

/***/ "./node_modules/ag-charts-enterprise/dist/package/main.esm.mjs":
/*!*********************************************************************!*\
  !*** ./node_modules/ag-charts-enterprise/dist/package/main.esm.mjs ***!
  \*********************************************************************/
/***/ ((__unused_webpack___webpack_module__, __webpack_exports__, __webpack_require__) => {


/***/ })

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/define property getters */
/******/ 	(() => {
/******/ 		// define getter functions for harmony exports
/******/ 		__webpack_require__.d = (exports, definition) => {
/******/ 			for(var key in definition) {
/******/ 				if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	(() => {
/******/ 		// define __esModule on exports
/******/ 		__webpack_require__.r = (exports) => {
/******/ 			if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 			}
/******/ 			Object.defineProperty(exports, '__esModule', { value: true });
/******/ 		};
/******/ 	})();
/******/ 	
/************************************************************************/
/******/ 	
/******/ 	// startup
/******/ 	// Load entry module and return exports
/******/ 	// This entry module can't be inlined because the eval devtool is used.
/******/ 	var __webpack_exports__ = __webpack_require__("./src/rendering_utils/resources/js/initAgCharts.js");
/******/ 	
/******/ })()
;