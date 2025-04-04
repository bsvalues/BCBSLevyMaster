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
            console.error('Error fetching API analytics:', error);
            // Show error state
            document.getElementById('total-calls').innerText = 'Error';
            document.getElementById('success-rate').innerText = 'Error';
            document.getElementById('avg-response-time').innerText = 'Error';
            document.getElementById('api-status-text').innerText = 'Error';
        });
}

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
    // (In a real implementation, this would use data from a time series endpoint)
    updateApiCallsTimeChart(data);
    
    // Update Calls by Service Chart
    updateServicesChart(data.calls_by_service || {});
    
    // Update Success vs Error Chart
    updateSuccessErrorChart(data.success_count || 0, data.error_count || 0);
    
    // Update Response Time Distribution Chart
    // (In a real implementation, this would use data from a dedicated endpoint)
    updateResponseTimeChart(data);
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
    // In a real implementation, this would use data from a time series endpoint
    // For now, we'll simulate data based on the total calls
    
    // Generate dates for the last 7 days
    const dates = [];
    const callCounts = [];
    const today = new Date();
    
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(today.getDate() - i);
        dates.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        
        // Simulate a distribution of calls
        // More calls in the middle of the week, fewer at the beginning and end
        const factor = 1 - Math.abs((i - 3) / 6);
        const callCount = Math.round((data.total_calls / 7) * (factor * 1.5 + 0.5));
        callCounts.push(callCount);
    }
    
    // Update chart
    apiCallsChart.data.labels = dates;
    apiCallsChart.data.datasets[0].data = callCounts;
    apiCallsChart.update();
}

/**
 * Function to update the Calls by Service Chart
 */
function updateServicesChart(serviceData) {
    const labels = [];
    const data = [];
    const backgroundColors = [];
    
    // Process the service data
    let index = 0;
    for (const [service, count] of Object.entries(serviceData)) {
        labels.push(service);
        data.push(count);
        
        // Assign a color from the color list
        if (index < chartColors.additionalColors.length) {
            backgroundColors.push(chartColors.additionalColors[index]);
        } else {
            // If we run out of colors, generate a random one
            backgroundColors.push(getRandomColor());
        }
        index++;
    }
    
    // If no services, show a placeholder
    if (labels.length === 0) {
        labels.push('No Data');
        data.push(1);
        backgroundColors.push(chartColors.secondary);
    }
    
    // Update chart
    servicesChart.data.labels = labels;
    servicesChart.data.datasets[0].data = data;
    servicesChart.data.datasets[0].backgroundColor = backgroundColors;
    servicesChart.update();
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
function updateResponseTimeChart(data) {
    // In a real implementation, this would use data from a dedicated endpoint
    // For now, we'll simulate data based on the average response time
    
    // Initialize buckets for response time distribution
    const buckets = [0, 0, 0, 0, 0]; // < 500ms, 500ms-1s, 1s-2s, 2s-5s, > 5s
    
    if (data.total_calls > 0 && data.avg_duration_ms) {
        // Simulate a normal distribution around the average
        const avgMs = data.avg_duration_ms;
        const totalCalls = data.total_calls;
        
        if (avgMs < 250) {
            // Mostly fast responses
            buckets[0] = Math.round(totalCalls * 0.7);
            buckets[1] = Math.round(totalCalls * 0.2);
            buckets[2] = Math.round(totalCalls * 0.07);
            buckets[3] = Math.round(totalCalls * 0.02);
            buckets[4] = Math.round(totalCalls * 0.01);
        } else if (avgMs < 750) {
            // Mix of fast and medium responses
            buckets[0] = Math.round(totalCalls * 0.4);
            buckets[1] = Math.round(totalCalls * 0.4);
            buckets[2] = Math.round(totalCalls * 0.15);
            buckets[3] = Math.round(totalCalls * 0.04);
            buckets[4] = Math.round(totalCalls * 0.01);
        } else if (avgMs < 1500) {
            // Mostly medium responses
            buckets[0] = Math.round(totalCalls * 0.1);
            buckets[1] = Math.round(totalCalls * 0.5);
            buckets[2] = Math.round(totalCalls * 0.3);
            buckets[3] = Math.round(totalCalls * 0.08);
            buckets[4] = Math.round(totalCalls * 0.02);
        } else if (avgMs < 3500) {
            // Slower responses
            buckets[0] = Math.round(totalCalls * 0.05);
            buckets[1] = Math.round(totalCalls * 0.15);
            buckets[2] = Math.round(totalCalls * 0.4);
            buckets[3] = Math.round(totalCalls * 0.3);
            buckets[4] = Math.round(totalCalls * 0.1);
        } else {
            // Very slow responses
            buckets[0] = Math.round(totalCalls * 0.02);
            buckets[1] = Math.round(totalCalls * 0.08);
            buckets[2] = Math.round(totalCalls * 0.2);
            buckets[3] = Math.round(totalCalls * 0.4);
            buckets[4] = Math.round(totalCalls * 0.3);
        }
    }
    
    // Ensure the sum equals the total calls
    let sum = buckets.reduce((a, b) => a + b, 0);
    if (sum < data.total_calls) {
        buckets[2] += (data.total_calls - sum);
    }
    
    // Update chart
    responseTimeChart.data.datasets[0].data = buckets;
    responseTimeChart.update();
}

/**
 * Function to fetch recent API calls
 */
function fetchRecentCalls(period, page, perPage, append = false) {
    const tableBody = document.getElementById('api-calls-table-body');
    const loadMoreBtn = document.getElementById('load-more-calls');
    
    // Show loading state if not appending
    if (!append) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center">
                    <div class="spinner-border spinner-border-sm text-primary me-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    Loading recent API calls...
                </td>
            </tr>
        `;
    }
    
    // Disable load more button while loading
    loadMoreBtn.disabled = true;
    loadMoreBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
    
    // Fetch data from the historical calls endpoint
    fetch(`/mcp/api/historical-calls?timeframe=${period}&page=${page}&per_page=${perPage}`)
        .then(response => response.json())
        .then(data => {
            // Re-enable load more button
            loadMoreBtn.disabled = false;
            loadMoreBtn.innerHTML = 'Load More';
            
            // Hide load more button if no more pages
            if (!data.meta.has_next) {
                loadMoreBtn.style.display = 'none';
            } else {
                loadMoreBtn.style.display = 'block';
            }
            
            // Clear table if not appending
            if (!append) {
                tableBody.innerHTML = '';
            }
            
            // If no calls, show a message
            if (data.calls.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center">
                            <i class="bi bi-info-circle me-2"></i>
                            No API calls found for this time period
                        </td>
                    </tr>
                `;
                return;
            }
            
            // Add rows to the table
            data.calls.forEach(call => {
                const row = document.createElement('tr');
                
                // Format timestamp
                const timestamp = new Date(call.timestamp);
                const formattedDate = timestamp.toLocaleDateString('en-US', { 
                    month: 'short', 
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                });
                
                // Create table cells
                row.innerHTML = `
                    <td>${formattedDate}</td>
                    <td><span class="service-tag">${call.service || 'N/A'}</span></td>
                    <td>${call.method || 'N/A'}</td>
                    <td>${call.duration_ms ? call.duration_ms.toFixed(0) + 'ms' : 'N/A'}</td>
                    <td class="status-${call.success ? 'success' : 'error'}">
                        ${call.success ? 
                            '<i class="bi bi-check-circle me-1"></i>Success' : 
                            '<i class="bi bi-x-circle me-1"></i>Error'}
                    </td>
                    <td>${call.error_message || '-'}</td>
                `;
                
                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error fetching historical calls:', error);
            
            // Re-enable load more button
            loadMoreBtn.disabled = false;
            loadMoreBtn.innerHTML = 'Load More';
            
            // Show error message if not appending
            if (!append) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center text-danger">
                            <i class="bi bi-exclamation-triangle me-2"></i>
                            Error loading API calls: ${error.message}
                        </td>
                    </tr>
                `;
            }
        });
}

/**
 * Helper function to convert hex color to rgba with opacity
 */
function hexToRgba(hex, opacity) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

/**
 * Helper function to generate random color
 */
function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}
