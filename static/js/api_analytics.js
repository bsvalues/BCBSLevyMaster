/**
 * API Analytics Dashboard JavaScript
 * 
 * This file contains the JavaScript code for the API Analytics dashboard,
 * including chart rendering, data fetching, and interactive elements.
 */

// Define chart objects globally so they can be updated
let apiCallsChart = null;
let servicesChart = null;
let successErrorChart = null;
let responseTimeChart = null;

// Define color schemes for charts
const chartColors = {
    primary: '#0d6efd',
    success: '#198754',
    danger: '#dc3545',
    warning: '#ffc107',
    info: '#0dcaf0',
    secondary: '#6c757d',
    light: '#f8f9fa',
    dark: '#212529',
    // Additional colors for charts with many data points
    additionalColors: [
        '#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4cc9f0',
        '#fb8500', '#219ebc', '#023047', '#ffb703', '#8ecae6'
    ]
};

// Initialize dashboard when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Default time period is 'week'
    let currentPeriod = 'week';
    let currentPage = 1;
    const perPage = 10;
    
    // Initialize charts
    initializeCharts();
    
    // Select time period buttons
    const timePeriodButtons = document.querySelectorAll('.time-period-btn');
    
    // Set up time period button click handlers
    timePeriodButtons.forEach(button => {
        button.addEventListener('click', function() {
            timePeriodButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            currentPeriod = this.dataset.period;
            currentPage = 1; // Reset to first page when changing time period
            
            // Update the display text
            const timeText = this.innerText;
            document.getElementById('calls-time-period').innerText = timeText;
            
            // Fetch new data for this time period
            fetchApiAnalytics(currentPeriod);
        });
    });
    
    // Set up refresh button handler
    document.getElementById('refresh-table').addEventListener('click', function() {
        fetchRecentCalls(currentPeriod, currentPage, perPage);
    });
    
    // Set up load more button handler
    document.getElementById('load-more-calls').addEventListener('click', function() {
        currentPage++;
        fetchRecentCalls(currentPeriod, currentPage, perPage, true);
    });
    
    // Initialize with the default time period
    fetchApiAnalytics(currentPeriod);
});

/**
 * Initialize all charts with default data
 */
function initializeCharts() {
    // API Calls Over Time Chart (Line Chart)
    const apiCallsChartCtx = document.getElementById('api-calls-chart').getContext('2d');
    apiCallsChart = new Chart(apiCallsChartCtx, {
        type: 'line',
        data: {
            labels: ['Loading...'],
            datasets: [{
                label: 'API Calls',
                data: [0],
                borderColor: chartColors.primary,
                backgroundColor: hexToRgba(chartColors.primary, 0.1),
                borderWidth: 2,
                pointBackgroundColor: chartColors.primary,
                pointRadius: 3,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    },
                    title: {
                        display: true,
                        text: 'Number of Calls'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            }
        }
    });
    
    // Calls by Service Chart (Doughnut Chart)
    const servicesChartCtx = document.getElementById('services-chart').getContext('2d');
    servicesChart = new Chart(servicesChartCtx, {
        type: 'doughnut',
        data: {
            labels: ['Loading...'],
            datasets: [{
                data: [1],
                backgroundColor: [chartColors.secondary],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12,
                        padding: 10
                    }
                }
            }
        }
    });
    
    // Success vs Error Rate Chart (Pie Chart)
    const successErrorChartCtx = document.getElementById('success-error-chart').getContext('2d');
    successErrorChart = new Chart(successErrorChartCtx, {
        type: 'pie',
        data: {
            labels: ['Success', 'Error'],
            datasets: [{
                data: [100, 0],
                backgroundColor: [chartColors.success, chartColors.danger],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true
                    }
                }
            }
        }
    });
    
    // Response Time Distribution Chart (Bar Chart)
    const responseTimeChartCtx = document.getElementById('response-time-chart').getContext('2d');
    responseTimeChart = new Chart(responseTimeChartCtx, {
        type: 'bar',
        data: {
            labels: ['< 500ms', '500ms - 1s', '1s - 2s', '2s - 5s', '> 5s'],
            datasets: [{
                label: 'Number of Calls',
                data: [0, 0, 0, 0, 0],
                backgroundColor: hexToRgba(chartColors.info, 0.7),
                borderColor: chartColors.info,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    },
                    title: {
                        display: true,
                        text: 'Number of Calls'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Response Time'
                    }
                }
            }
        }
    });
}

/**
 * Function to fetch API analytics data for a given time period
 */
function fetchApiAnalytics(period) {
    // Show loading state
    document.getElementById('total-calls').innerText = 'Loading...';
    document.getElementById('success-rate').innerText = 'Loading...';
    document.getElementById('avg-response-time').innerText = 'Loading...';
    document.getElementById('api-status-text').innerText = 'Loading...';
    
    // Fetch data from the API statistics endpoint
    fetch(`/mcp/api/statistics?timeframe=${period}&historical=true`)
        .then(response => response.json())
        .then(data => {
            // Update dashboard metrics
            updateDashboardMetrics(data);
            
            // Update charts with the new data
            updateCharts(data);
            
            // Fetch and update the recent calls table
            fetchRecentCalls(period, 1, 10);
        })
        .catch(error => {
            console.error("Error fetching API analytics:", error);
            console.log("Error details:", JSON.stringify(error));
            // Show error state
            document.getElementById("total-calls").innerText = "Error";
            document.getElementById("success-rate").innerText = "Error";
            document.getElementById("avg-response-time").innerText = "Error";
            document.getElementById("api-status-text").innerText = "Error";
        });

/**
 * Function to update dashboard metrics with new data
 */
function updateDashboardMetrics(data) {
    // Update total calls
    document.getElementById('total-calls').innerText = data.total_calls || 0;
    
    // Calculate success rate
    let successRate = 'N/A';
    if (data.total_calls > 0) {
        const successPercent = (data.success_count / data.total_calls) * 100;
        successRate = `${successPercent.toFixed(1)}%`;
    }
    document.getElementById('success-rate').innerText = successRate;
    
    // Update success count text
    const successCount = data.success_count || 0;
    document.getElementById('success-count').innerText = `${successCount} successful calls`;
    
    // Update average response time
    const avgResponseTime = data.avg_duration_ms ? `${data.avg_duration_ms.toFixed(0)}ms` : 'N/A';
    document.getElementById('avg-response-time').innerText = avgResponseTime;
    
    // Update response time progress bar (assuming 2000ms is max for 100%)
    const responseTimePercent = Math.min((data.avg_duration_ms || 0) / 2000 * 100, 100);
    document.getElementById('response-time-bar').style.width = `${responseTimePercent}%`;
    
    // Update API status
    const apiStatus = data.summary ? data.summary.status : 'inactive';
    document.getElementById('api-status-text').innerText = apiStatus.charAt(0).toUpperCase() + apiStatus.slice(1);
    
    // Update status badge
    const statusBadge = document.getElementById('api-status-badge');
    statusBadge.innerText = data.summary ? data.summary.message : 'No data available';
    statusBadge.className = 'status-badge';
    statusBadge.classList.add(`status-${apiStatus}`);
}

/**
 * Function to update all charts with new data
 */
function updateCharts(data) {
    // If we don't have enough data, show a placeholder
    if (!data.total_calls || data.total_calls === 0) {
        updateChartsWithNoData();
        return;
    }
    
    // Update API Calls Over Time Chart
    updateApiCallsTimeChart(data);
    
    // Update Calls by Service Chart - Using dedicated endpoint
    updateServicesChart();
    
    // Update Success vs Error Chart
    updateSuccessErrorChart(data.success_count || 0, data.error_count || 0);
    
    // Update Response Time Distribution Chart - Using dedicated endpoint
    updateResponseTimeChart();
}

/**
 * Function to update charts when no data is available
 */
function updateChartsWithNoData() {
    // API Calls Over Time Chart
    apiCallsChart.data.labels = ['No Data'];
    apiCallsChart.data.datasets[0].data = [0];
    apiCallsChart.update();
    
    // Calls by Service Chart
    servicesChart.data.labels = ['No Data'];
    servicesChart.data.datasets[0].data = [1];
    servicesChart.data.datasets[0].backgroundColor = [chartColors.secondary];
    servicesChart.update();
    
    // Success vs Error Chart
    successErrorChart.data.labels = ['No Data'];
    successErrorChart.data.datasets[0].data = [1];
    successErrorChart.data.datasets[0].backgroundColor = [chartColors.secondary];
    successErrorChart.update();
    
    // Response Time Distribution Chart
    responseTimeChart.data.datasets[0].data = [0, 0, 0, 0, 0];
    responseTimeChart.update();
}

/**
 * Function to update the API Calls Over Time Chart
 */
function updateApiCallsTimeChart(data) {
    // Show loading state
    apiCallsChart.data.labels = ['Loading...'];
    apiCallsChart.data.datasets[0].data = [0];
    apiCallsChart.update();
    
    // Get the current time period
    const period = document.querySelector('.time-period-btn.active').dataset.period;
    
    // Determine appropriate interval based on time period
    let interval = 'day';
    if (period === 'day') {
        interval = 'hour';
    } else if (period === 'month') {
        interval = 'day';
    } else if (period === 'all') {
        interval = 'week';
    }
    
    // Fetch data from the timeseries endpoint
    fetch(`/mcp/api/timeseries?timeframe=${period}&interval=${interval}`)
        .then(response => response.json())
        .then(timeData => {
            if (timeData.error) {
                console.error('Error from timeseries endpoint:', timeData.message);
                return;
            }
            
            // Format the data for the chart
            const labels = [];
            const totalCalls = [];
            const successCalls = [];
            const errorCalls = [];
            
            if (timeData.data_points && timeData.data_points.length > 0) {
                timeData.data_points.forEach(point => {
                    // Format the timestamp based on interval
                    const date = new Date(point.timestamp);
                    let formattedDate;
                    
                    if (interval === 'hour') {
                        formattedDate = date.toLocaleTimeString('en-US', { 
                            hour: '2-digit', 
                            minute: '2-digit' 
                        });
                    } else if (interval === 'day') {
                        formattedDate = date.toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric' 
                        });
                    } else if (interval === 'week') {
                        formattedDate = `Week of ${date.toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric' 
                        })}`;
                    } else {
                        formattedDate = date.toLocaleDateString('en-US', { 
                            month: 'long', 
                            year: 'numeric' 
                        });
                    }
                    
                    labels.push(formattedDate);
                    totalCalls.push(point.total);
                    successCalls.push(point.success);
                    errorCalls.push(point.error);
                });
                
                // Update chart with real data
                apiCallsChart.data.labels = labels;
                apiCallsChart.data.datasets = [
                    {
                        label: 'Total Calls',
                        data: totalCalls,
                        borderColor: chartColors.primary,
                        backgroundColor: hexToRgba(chartColors.primary, 0.1),
                        borderWidth: 2,
                        pointBackgroundColor: chartColors.primary,
                        pointRadius: 3,
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: 'Success',
                        data: successCalls,
                        borderColor: chartColors.success,
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        pointBackgroundColor: chartColors.success,
                        pointRadius: 3,
                        tension: 0.3,
                        fill: false
                    },
                    {
                        label: 'Error',
                        data: errorCalls,
                        borderColor: chartColors.danger,
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        pointBackgroundColor: chartColors.danger,
                        pointRadius: 3,
                        tension: 0.3,
                        fill: false
                    }
                ];
            } else {
                // No data available
                apiCallsChart.data.labels = ['No Data'];
                apiCallsChart.data.datasets = [{
                    label: 'API Calls',
                    data: [0],
                    borderColor: chartColors.primary,
                    backgroundColor: hexToRgba(chartColors.primary, 0.1),
                    borderWidth: 2,
                    pointBackgroundColor: chartColors.primary,
                    pointRadius: 3,
                    tension: 0.3,
                    fill: true
                }];
            }
            
            apiCallsChart.update();
        })
        .catch(error => {
            console.error('Error fetching time series data:', error);
            // Show error state
            apiCallsChart.data.labels = ['Error loading data'];
            apiCallsChart.data.datasets[0].data = [0];
            apiCallsChart.update();
        });
}

/**
 * Function to update the Calls by Service Chart
 */
function updateServicesChart() {
    // Show loading state
    servicesChart.data.labels = ['Loading...'];
    servicesChart.data.datasets[0].data = [1];
    servicesChart.data.datasets[0].backgroundColor = [chartColors.secondary];
    servicesChart.update();
    
    // Get the current time period
    const period = document.querySelector('.time-period-btn.active').dataset.period;
    
    // Fetch data from the service breakdown endpoint
    fetch(`/mcp/api/service-breakdown?timeframe=${period}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error from service breakdown endpoint:', data.message);
                return;
            }
            
            const labels = [];
            const callData = [];
            const backgroundColors = [];
            
            // Process the service data
            if (data.services && data.services.length > 0) {
                let index = 0;
                data.services.forEach(service => {
                    labels.push(service.service);
                    callData.push(service.total_calls);
                    
                    // Assign a color from the color list
                    if (index < chartColors.additionalColors.length) {
                        backgroundColors.push(chartColors.additionalColors[index]);
                    } else {
                        // If we run out of colors, generate a random one
                        backgroundColors.push(getRandomColor());
                    }
                    index++;
                });
            } else {
                // No data available
                labels.push('No Data');
                callData.push(1);
                backgroundColors.push(chartColors.secondary);
            }
            
            // Update chart
            servicesChart.data.labels = labels;
            servicesChart.data.datasets[0].data = callData;
            servicesChart.data.datasets[0].backgroundColor = backgroundColors;
            servicesChart.update();
        })
        .catch(error => {
            console.error('Error fetching service breakdown data:', error);
            // Show error state
            servicesChart.data.labels = ['Error loading data'];
            servicesChart.data.datasets[0].data = [1];
            servicesChart.data.datasets[0].backgroundColor = [chartColors.danger];
            servicesChart.update();
        });
}

/**
 * Function to update the Success vs Error Chart
 */
function updateSuccessErrorChart(successCount, errorCount) {
    // If no data, show a placeholder
    if (successCount === 0 && errorCount === 0) {
        successErrorChart.data.labels = ['No Data'];
        successErrorChart.data.datasets[0].data = [1];
        successErrorChart.data.datasets[0].backgroundColor = [chartColors.secondary];
    } else {
        successErrorChart.data.labels = ['Success', 'Error'];
        successErrorChart.data.datasets[0].data = [successCount, errorCount];
        successErrorChart.data.datasets[0].backgroundColor = [chartColors.success, chartColors.danger];
    }
    
    successErrorChart.update();
}

/**
 * Function to update the Response Time Distribution Chart
 */
function updateResponseTimeChart() {
    // Show loading state
    responseTimeChart.data.datasets[0].data = [0, 0, 0, 0, 0];
    responseTimeChart.update();
    
    // Get the current time period
    const period = document.querySelector('.time-period-btn.active').dataset.period;
    
    // Fetch data from the response time distribution endpoint
    fetch(`/mcp/api/response-time-distribution?timeframe=${period}`)
        .then(response => response.json())
        .then(timeData => {
            if (timeData.error) {
                console.error('Error from response time distribution endpoint:', timeData.message);
                return;
            }
            
            // Format the data for the chart
            const buckets = [
                timeData.buckets.under_500ms || 0,
                timeData.buckets['500ms_to_1s'] || 0,
                timeData.buckets['1s_to_2s'] || 0,
                timeData.buckets['2s_to_5s'] || 0,
                timeData.buckets.over_5s || 0
            ];
            
            // Update chart
            responseTimeChart.data.datasets[0].data = buckets;
            responseTimeChart.update();
        })
        .catch(error => {
            console.error('Error fetching response time distribution data:', error);
            // Show error state
            responseTimeChart.data.datasets[0].data = [0, 0, 0, 0, 0];
            responseTimeChart.update();
        });
}

/**
 * Function to fetch recent API calls for a given time period, page, and per page count
 */
function fetchRecentCalls(period, page, perPage, append = false) {
    // Show loading state
    if (!append) {
        document.getElementById('recent-calls-table').innerHTML = `
            <tr>
                <td colspan="5" class="text-center">
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Loading...
                </td>
            </tr>
        `;
    }
    
    // Fetch data from the historical calls endpoint
    fetch(`/mcp/api/historical-calls?timeframe=${period}&page=${page}&per_page=${perPage}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error from historical calls endpoint:', data.message);
                document.getElementById('recent-calls-table').innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center text-danger">
                            Error loading data
                        </td>
                    </tr>
                `;
                return;
            }
            
            // If no data, show empty state
            if (!data.calls || data.calls.length === 0) {
                document.getElementById('recent-calls-table').innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center">
                            No API calls found for this time period
                        </td>
                    </tr>
                `;
                
                // Hide load more button
                document.getElementById('load-more-calls').style.display = 'none';
                return;
            }
            
            // Format and display recent calls
            let tableHtml = '';
            if (append) {
                tableHtml = document.getElementById('recent-calls-table').innerHTML;
            }
            
            data.calls.forEach(call => {
                // Format the timestamp
                const date = new Date(call.timestamp);
                const formattedTime = date.toLocaleString('en-US', { 
                    month: 'short', 
                    day: 'numeric', 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit' 
                });
                
                // Format the status badge
                const statusClass = call.success ? 'success' : 'danger';
                const statusText = call.success ? 'Success' : 'Error';
                
                // Format the duration with appropriate units
                let duration = 'N/A';
                if (call.duration_ms) {
                    duration = call.duration_ms.toFixed(0) + 'ms';
                }
                
                // Format the error message (truncate if too long)
                let errorMessage = call.error_message || '';
                if (errorMessage.length > 50) {
                    errorMessage = errorMessage.substring(0, 47) + '...';
                }
                
                tableHtml += `
                    <tr>
                        <td>${formattedTime}</td>
                        <td>${call.service}</td>
                        <td>${call.method}</td>
                        <td>${duration}</td>
                        <td>
                            <span class="badge bg-${statusClass}">${statusText}</span>
                            ${errorMessage ? `<div class="small text-muted mt-1">${errorMessage}</div>` : ''}
                        </td>
                    </tr>
                `;
            });
            
            // Update table with the data
            document.getElementById('recent-calls-table').innerHTML = tableHtml;
            
            // Update pagination controls
            document.getElementById('load-more-calls').style.display = data.meta.has_next ? 'block' : 'none';
            
            // If pagination info is available, update the info text
            if (data.meta) {
                const start = (data.meta.page - 1) * data.meta.per_page + 1;
                const end = Math.min(start + data.meta.per_page - 1, data.meta.total_count);
                document.getElementById('pagination-info').innerHTML = `
                    Showing <span class="fw-bold">${start}-${end}</span> of <span class="fw-bold">${data.meta.total_count}</span> calls
                `;
            }
        })
        .catch(error => {
            console.error('Error fetching recent calls:', error);
            // Show error state
            if (!append) {
                document.getElementById('recent-calls-table').innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center text-danger">
                            Error loading data
                        </td>
                    </tr>
                `;
            }
        });
}

/**
 * Helper function to convert hex color to rgba
 */
function hexToRgba(hex, alpha = 1) {
    const [r, g, b] = hex.match(/\w\w/g).map(x => parseInt(x, 16));
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Helper function to generate a random color
 */
function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

/**
 * Helper function to format a date as a string
 */
function formatDate(date) {
    return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric' 
    });
}
