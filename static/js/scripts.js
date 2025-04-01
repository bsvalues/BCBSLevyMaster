/**
 * Custom JavaScript for Levy Calculation System
 */

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => 
        new bootstrap.Tooltip(tooltipTriggerEl)
    );
    
    // Initialize Bootstrap popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    const popoverList = [...popoverTriggerList].map(popoverTriggerEl => 
        new bootstrap.Popover(popoverTriggerEl)
    );
    
    // Year selector handling
    const yearSelector = document.querySelector('.year-selector');
    if (yearSelector) {
        yearSelector.addEventListener('change', function() {
            const year = this.value;
            // Store the selected year in session storage
            sessionStorage.setItem('selectedYear', year);
            // Redirect to the same page with the year parameter
            const url = new URL(window.location.href);
            url.searchParams.set('year', year);
            window.location.href = url.toString();
        });
    }
    
    // Handle tax term tooltips
    const taxTerms = document.querySelectorAll('.tax-term');
    if (taxTerms.length > 0) {
        taxTerms.forEach(term => {
            term.addEventListener('click', function(e) {
                e.preventDefault();
                const termId = this.getAttribute('data-term-id');
                showTermDefinition(termId);
            });
        });
    }
    
    // Handle file uploads
    const fileUpload = document.getElementById('fileUpload');
    if (fileUpload) {
        fileUpload.addEventListener('change', function() {
            const fileLabel = document.querySelector('.custom-file-label');
            if (fileLabel) {
                fileLabel.textContent = this.files[0].name;
            }
            
            // Show file details
            const fileDetails = document.getElementById('fileDetails');
            if (fileDetails && this.files.length > 0) {
                const file = this.files[0];
                const fileSize = formatFileSize(file.size);
                const fileType = file.type || 'Unknown';
                
                fileDetails.innerHTML = `
                    <div class="alert alert-info">
                        <strong>File Selected:</strong> ${file.name}<br>
                        <strong>Size:</strong> ${fileSize}<br>
                        <strong>Type:</strong> ${fileType}
                    </div>
                `;
                fileDetails.classList.remove('d-none');
            }
        });
    }
    
    // Scenario form handling
    const scenarioForm = document.getElementById('scenarioForm');
    if (scenarioForm) {
        // Add new adjustment row
        const addAdjustmentBtn = document.getElementById('addAdjustment');
        if (addAdjustmentBtn) {
            addAdjustmentBtn.addEventListener('click', function() {
                const adjustmentsContainer = document.getElementById('adjustmentsContainer');
                const index = document.querySelectorAll('.adjustment-row').length;
                
                const newRow = document.createElement('div');
                newRow.className = 'adjustment-row row mb-3';
                newRow.innerHTML = `
                    <div class="col-md-4">
                        <select name="tax_code_id_${index}" class="form-select" required>
                            <option value="">Select Tax Code</option>
                            ${document.querySelector('select[name="tax_code_id_0"]').innerHTML.split('<option value="">Select Tax Code</option>')[1]}
                        </select>
                    </div>
                    <div class="col-md-3">
                        <select name="adjustment_type_${index}" class="form-select" required>
                            <option value="percentage">Percentage</option>
                            <option value="fixed_amount">Fixed Amount</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <input type="number" name="adjustment_value_${index}" class="form-control" step="0.01" required>
                    </div>
                    <div class="col-md-2">
                        <button type="button" class="btn btn-danger remove-adjustment">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                `;
                
                adjustmentsContainer.appendChild(newRow);
                
                // Add event listener to the remove button
                newRow.querySelector('.remove-adjustment').addEventListener('click', function() {
                    newRow.remove();
                });
            });
        }
        
        // Form submission
        scenarioForm.addEventListener('submit', function(e) {
            // Update the hidden input with the number of adjustments
            const adjustmentCount = document.querySelectorAll('.adjustment-row').length;
            document.getElementById('adjustmentCount').value = adjustmentCount;
        });
    }
    
    // Charts initialization
    initCharts();
    
    // Datatable initialization
    initDataTables();
});

/**
 * Format file size to human-readable format
 * @param {number} bytes - Size in bytes
 * @returns {string} - Formatted size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    
    return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Show tax term definition in a modal
 * @param {string} termId - ID of the tax term
 */
function showTermDefinition(termId) {
    // Fetch the definition from the server
    fetch(`/api/glossary/term/${termId}`)
        .then(response => response.json())
        .then(data => {
            const modal = new bootstrap.Modal(document.getElementById('termModal'));
            document.getElementById('termTitle').textContent = data.term;
            document.getElementById('termDefinition').innerHTML = `
                <p class="fw-bold">Technical Definition:</p>
                <p>${data.technical_definition}</p>
                <p class="fw-bold">Plain Language:</p>
                <p>${data.plain_language}</p>
                <p class="fw-bold">Example:</p>
                <p>${data.example}</p>
            `;
            modal.show();
        })
        .catch(error => {
            console.error('Error fetching term definition:', error);
        });
}

/**
 * Initialize charts on the page
 */
function initCharts() {
    // Only proceed if Chart.js is loaded
    if (typeof Chart === 'undefined') return;
    
    // Levy Rates Chart
    const levyRatesCanvas = document.getElementById('levyRatesChart');
    if (levyRatesCanvas) {
        const ctx = levyRatesCanvas.getContext('2d');
        const levyRatesData = JSON.parse(levyRatesCanvas.dataset.chartData || '{}');
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: levyRatesData.labels || [],
                datasets: [{
                    label: 'Levy Rate (per $1,000)',
                    data: levyRatesData.data || [],
                    backgroundColor: 'rgba(13, 110, 253, 0.7)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Rate per $1,000 Assessed Value'
                        }
                    }
                }
            }
        });
    }
    
    // Historical Trends Chart
    const historicalTrendsCanvas = document.getElementById('historicalTrendsChart');
    if (historicalTrendsCanvas) {
        const ctx = historicalTrendsCanvas.getContext('2d');
        const historicalData = JSON.parse(historicalTrendsCanvas.dataset.chartData || '{}');
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: historicalData.years || [],
                datasets: [{
                    label: 'Levy Amount ($)',
                    data: historicalData.levy_amounts || [],
                    backgroundColor: 'rgba(25, 135, 84, 0.2)',
                    borderColor: 'rgba(25, 135, 84, 1)',
                    borderWidth: 2,
                    tension: 0.1,
                    yAxisID: 'y'
                },
                {
                    label: 'Assessed Value ($)',
                    data: historicalData.assessed_values || [],
                    backgroundColor: 'rgba(13, 110, 253, 0.2)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 2,
                    tension: 0.1,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Levy Amount ($)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false,
                        },
                        title: {
                            display: true,
                            text: 'Assessed Value ($)'
                        }
                    }
                }
            }
        });
    }
    
    // Forecast Chart
    const forecastCanvas = document.getElementById('forecastChart');
    if (forecastCanvas) {
        const ctx = forecastCanvas.getContext('2d');
        const forecastData = JSON.parse(forecastCanvas.dataset.chartData || '{}');
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: forecastData.years || [],
                datasets: [{
                    label: 'Historical Data',
                    data: forecastData.historical || [],
                    backgroundColor: 'rgba(13, 110, 253, 0.2)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 2,
                    pointRadius: 4,
                    tension: 0.1
                },
                {
                    label: 'Linear Forecast',
                    data: forecastData.linear || [],
                    backgroundColor: 'rgba(25, 135, 84, 0.2)',
                    borderColor: 'rgba(25, 135, 84, 1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHitRadius: 10,
                    borderDash: [5, 5],
                    tension: 0.1
                },
                {
                    label: 'ARIMA Forecast',
                    data: forecastData.arima || [],
                    backgroundColor: 'rgba(220, 53, 69, 0.2)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHitRadius: 10,
                    borderDash: [5, 5],
                    tension: 0.1
                },
                {
                    label: 'AI Enhanced Forecast',
                    data: forecastData.ai || [],
                    backgroundColor: 'rgba(111, 66, 193, 0.2)',
                    borderColor: 'rgba(111, 66, 193, 1)',
                    borderWidth: 3,
                    pointRadius: 0,
                    pointHitRadius: 10,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: forecastData.y_axis_label || 'Value'
                        }
                    }
                }
            }
        });
    }
}

/**
 * Initialize DataTables on the page
 */
function initDataTables() {
    // Only proceed if DataTable is loaded
    if (typeof $.fn.DataTable === 'undefined') return;
    
    $('.data-table').each(function() {
        $(this).DataTable({
            responsive: true,
            pageLength: 25,
            language: {
                search: "Filter records:",
                paginate: {
                    previous: '<i class="bi bi-chevron-left"></i>',
                    next: '<i class="bi bi-chevron-right"></i>'
                }
            }
        });
    });
}

/**
 * Show a confirmation dialog
 * @param {string} message - Message to display
 * @param {function} callback - Function to call if confirmed
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Format currency values
 * @param {number} value - The value to format
 * @returns {string} - Formatted currency string
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(value);
}

/**
 * Format percentage values
 * @param {number} value - The value to format
 * @returns {string} - Formatted percentage string
 */
function formatPercentage(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}