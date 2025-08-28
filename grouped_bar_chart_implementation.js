// Grouped Bar Chart Implementation for Price Comparison
// This implementation creates a chart where each product is a group, 
// and each restaurant is a bar within that group

let groupedProfitChart = null;

// Color palette for restaurants (consistent colors)
const restaurantColors = [
    { bg: 'rgba(255, 99, 132, 0.8)', border: 'rgb(255, 99, 132)' },
    { bg: 'rgba(54, 162, 235, 0.8)', border: 'rgb(54, 162, 235)' },
    { bg: 'rgba(255, 205, 86, 0.8)', border: 'rgb(255, 205, 86)' },
    { bg: 'rgba(75, 192, 192, 0.8)', border: 'rgb(75, 192, 192)' },
    { bg: 'rgba(153, 102, 255, 0.8)', border: 'rgb(153, 102, 255)' },
    { bg: 'rgba(255, 159, 64, 0.8)', border: 'rgb(255, 159, 64)' },
    { bg: 'rgba(199, 199, 199, 0.8)', border: 'rgb(199, 199, 199)' },
    { bg: 'rgba(83, 102, 255, 0.8)', border: 'rgb(83, 102, 255)' }
];

function initializeGroupedBarChart() {
    const ctx = document.getElementById('profit-chart').getContext('2d');
    
    groupedProfitChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [], // Product names
            datasets: [] // Restaurant datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Confronto Gross Profit per Prodotto e Ristorante',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return 'Prodotto: ' + context[0].label;
                        },
                        label: function(context) {
                            const restaurantName = context.dataset.label;
                            const profit = context.parsed.y;
                            const scenario = document.querySelector('input[name="profit-type"]:checked')?.value === 'delivery' ? 'Delivery' : 'On Site';
                            const profitColor = profit >= 0 ? '🟢' : '🔴';
                            return `${profitColor} ${restaurantName} (${scenario}): €${profit.toFixed(2)}`;
                        },
                        footer: function(context) {
                            if (context.length > 1) {
                                const profits = context.map(item => item.parsed.y);
                                const avgProfit = profits.reduce((sum, p) => sum + p, 0) / profits.length;
                                return `Media prodotto: €${avgProfit.toFixed(2)}`;
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Gross Profit (€)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        callback: function(value) {
                            return '€' + value.toFixed(2);
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Prodotti',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0,
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function updateGroupedBarChart(isDelivery = false) {
    if (!groupedProfitChart) return;
    
    // Get selected restaurants
    const selectedRestaurants = Array.from(document.querySelectorAll('.restaurant-chart-filter:checked'))
        .map(cb => parseInt(cb.value));
    
    if (selectedRestaurants.length === 0) {
        groupedProfitChart.data.labels = [];
        groupedProfitChart.data.datasets = [];
        groupedProfitChart.update();
        return;
    }
    
    // Organize data by product and restaurant
    const productData = {};
    const restaurantNames = {};
    
    comparisonData.forEach(item => {
        const filteredListings = item.listings.filter(listing => 
            selectedRestaurants.includes(listing.restaurantId) && listing.isAvailable
        );
        
        if (filteredListings.length > 0) {
            productData[item.productName] = {};
            
            filteredListings.forEach(listing => {
                const profit = isDelivery ? listing.deliveryProfit : listing.localProfit;
                productData[item.productName][listing.restaurantId] = profit;
                restaurantNames[listing.restaurantId] = listing.restaurantName;
            });
        }
    });
    
    // Create datasets (one per restaurant)
    const datasets = [];
    const productNames = Object.keys(productData);
    
    selectedRestaurants.forEach((restaurantId, index) => {
        const restaurantName = restaurantNames[restaurantId];
        if (!restaurantName) return;
        
        const data = productNames.map(productName => {
            return productData[productName][restaurantId] || 0;
        });
        
        const colorIndex = index % restaurantColors.length;
        
        datasets.push({
            label: restaurantName,
            data: data,
            backgroundColor: restaurantColors[colorIndex].bg,
            borderColor: restaurantColors[colorIndex].border,
            borderWidth: 1,
            borderRadius: 2,
            maxBarThickness: 40
        });
    });
    
    // Update chart
    groupedProfitChart.data.labels = productNames;
    groupedProfitChart.data.datasets = datasets;
    
    // Update chart title based on scenario
    const scenario = isDelivery ? 'Delivery' : 'On Site';
    groupedProfitChart.options.plugins.title.text = `Confronto Gross Profit ${scenario} per Prodotto e Ristorante`;
    
    groupedProfitChart.update();
}

// Chart controls
function toggleChartScenario() {
    const isDelivery = document.querySelector('input[name="profit-type"]:checked')?.value === 'delivery';
    updateGroupedBarChart(isDelivery);
}

function selectAllRestaurantsForChart() {
    document.querySelectorAll('.restaurant-chart-filter').forEach(cb => {
        cb.checked = true;
    });
    toggleChartScenario();
}

function clearAllRestaurantsForChart() {
    document.querySelectorAll('.restaurant-chart-filter').forEach(cb => {
        cb.checked = false;
    });
    toggleChartScenario();
}

// Chart sorting functions
function sortChartByProfit() {
    if (!groupedProfitChart || !groupedProfitChart.data.labels.length) return;
    
    // Calculate average profit for each product
    const productProfits = groupedProfitChart.data.labels.map((label, index) => {
        const profits = groupedProfitChart.data.datasets.map(dataset => dataset.data[index] || 0);
        const avgProfit = profits.reduce((sum, p) => sum + p, 0) / profits.length;
        return { label, avgProfit, index };
    });
    
    // Sort by average profit (descending)
    productProfits.sort((a, b) => b.avgProfit - a.avgProfit);
    
    // Reorder data
    const newLabels = productProfits.map(p => p.label);
    const newDatasets = groupedProfitChart.data.datasets.map(dataset => ({
        ...dataset,
        data: productProfits.map(p => dataset.data[p.index])
    }));
    
    groupedProfitChart.data.labels = newLabels;
    groupedProfitChart.data.datasets = newDatasets;
    groupedProfitChart.update();
}

function sortChartByName() {
    if (!groupedProfitChart || !groupedProfitChart.data.labels.length) return;
    
    // Create sorting index
    const sortedIndices = groupedProfitChart.data.labels
        .map((label, index) => ({ label, index }))
        .sort((a, b) => a.label.localeCompare(b.label))
        .map(item => item.index);
    
    // Reorder data
    const newLabels = sortedIndices.map(i => groupedProfitChart.data.labels[i]);
    const newDatasets = groupedProfitChart.data.datasets.map(dataset => ({
        ...dataset,
        data: sortedIndices.map(i => dataset.data[i])
    }));
    
    groupedProfitChart.data.labels = newLabels;
    groupedProfitChart.data.datasets = newDatasets;
    groupedProfitChart.update();
}

// Export chart data
function exportChartData() {
    if (!groupedProfitChart || !groupedProfitChart.data.labels.length) {
        alert('Nessun dato da esportare nel grafico');
        return;
    }
    
    const scenario = document.querySelector('input[name="profit-type"]:checked')?.value === 'delivery' ? 'Delivery' : 'OnSite';
    
    let csv = `Prodotto,${groupedProfitChart.data.datasets.map(d => d.label).join(',')}\n`;
    
    groupedProfitChart.data.labels.forEach((product, productIndex) => {
        const row = [product];
        groupedProfitChart.data.datasets.forEach(dataset => {
            row.push((dataset.data[productIndex] || 0).toFixed(2));
        });
        csv += row.join(',') + '\n';
    });
    
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `gross_profit_${scenario}_${new Date().toISOString().slice(0, 10)}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeGroupedBarChart();
    
    // Set up event listeners for chart controls
    document.querySelectorAll('input[name="profit-type"]').forEach(radio => {
        radio.addEventListener('change', toggleChartScenario);
    });
    
    document.querySelectorAll('.restaurant-chart-filter').forEach(cb => {
        cb.addEventListener('change', toggleChartScenario);
    });
    
    // Initial chart update
    toggleChartScenario();
});