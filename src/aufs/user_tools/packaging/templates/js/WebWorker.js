// WebWorker.js
onmessage = function(e) {
    const parsedData = JSON.parse(e.data);
    postMessage(parsedData);
};
