/**
 * scripts.js - Main JavaScript for Levy Calculation System
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize sidebar toggle
    initSidebar();
    
    // Initialize theme toggle
    initThemeToggle();
    
    // Initialize tooltips and popovers
    initTooltips();
    
    // Initialize charts if they exist on the page
    initCharts();
    
    // Initialize file uploads if they exist on the page
    setupFileUpload();
    
    // Initialize multi-select dropdowns
    setupMultiselect();
    
    // Add event listeners for dashboard refresh button
    const refreshBtn = document.getElementById('refreshDashboard');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshDashboardData);
    }
});

/**
 * Initialize sidebar toggle functionality
 */
function initSidebar() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarMenu = document.getElementById('sidebarMenu');
    
    if (sidebarToggle && sidebarMenu) {
        sidebarToggle.addEventListener('click', function() {
            sidebarMenu.classList.toggle('show');
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(event) {
            const isClickInside = sidebarMenu.contains(event.target) || sidebarToggle.contains(event.target);
            
            if (!isClickInside && sidebarMenu.classList.contains('show') && window.innerWidth < 768) {
                sidebarMenu.classList.remove('show');
            }
        });
    }
}

/**
 * Initialize theme toggle functionality
 */
function initThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    const htmlElement = document.documentElement;
    
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            const iconClass = newTheme === 'dark' ? 'bi-moon-stars' : 'bi-sun';
            
            htmlElement.setAttribute('data-bs-theme', newTheme);
            themeToggle.querySelector('i').className = `bi ${iconClass}`;
            
            // Store preference in localStorage
            localStorage.setItem('theme', newTheme);
        });
        
        // Apply saved theme preference
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            htmlElement.setAttribute('data-bs-theme', savedTheme);
            const iconClass = savedTheme === 'dark' ? 'bi-moon-stars' : 'bi-sun';
            themeToggle.querySelector('i').className = `bi ${iconClass}`;
        }
    }
}

/**
 * Initialize Bootstrap tooltips and popovers
 */
function initTooltips() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Initialize chart elements on the page
 */
function initCharts() {
    // Initialize historical rates chart
    const historicalRatesChart = document.getElementById('historicalRatesChart');
    if (historicalRatesChart && window.historicalData) {
        new Chart(historicalRatesChart, {
            type: 'line',
            data: {
                labels: window.historicalData.years,
                datasets: window.historicalData.datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Levy Rate (per $1,000)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Year'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': $' + context.raw.toFixed(2) + ' per $1,000';
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                }
            }
        });
    }
    
    // Initialize tax distribution chart in modal
    const taxDistributionChart = document.getElementById('taxDistributionChart');
    if (taxDistributionChart && window.taxDistData) {
        new Chart(taxDistributionChart, {
            type: 'doughnut',
            data: {
                labels: window.taxDistData.labels,
                datasets: [{
                    data: window.taxDistData.values,
                    backgroundColor: [
                        '#3498db',
                        '#2ecc71',
                        '#1abc9c',
                        '#f1c40f',
                        '#95a5a6'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ' + context.raw + '%';
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Refresh dashboard data and update UI elements
 */
function refreshDashboardData() {
    showLoadingOverlay('Refreshing dashboard data...');
    
    // Simulate API call with setTimeout
    setTimeout(function() {
        hideLoadingOverlay();
        
        // Update AI Insights section
        refreshAIInsights();
        
        // Show success notification
        showNotification('Dashboard data refreshed successfully!', 'success');
    }, 1500);
}

/**
 * AI-powered insights functionality
 */
function refreshAIInsights() {
    const aiInsights = document.getElementById('aiInsights');
    if (!aiInsights) return;
    
    // Show loading state
    aiInsights.innerHTML = `
        <div class="d-flex justify-content-center align-items-center p-5">
            <div class="spinner-border text-info" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span class="ms-3">Generating AI insights...</span>
        </div>
    `;
    
    // Simulate AI processing delay
    setTimeout(function() {
        // Replace with actual AI-generated insights
        aiInsights.innerHTML = `
            <div class="p-3">
                <h6 class="text-muted">Trends & Anomalies</h6>
                <ul class="list-group list-group-flush">
                    <li class="list-group-item bg-dark border-secondary ai-insight fade-in">
                        School District 312 shows a 5.2% increase in assessed values, above the county average of 3.1%.
                        <span class="ai-badge">Trend</span>
                    </li>
                    <li class="list-group-item bg-dark border-secondary ai-insight fade-in" style="animation-delay: 0.2s">
                        Hospital District #2 has an unusually high variance in assessed values across property types.
                        <span class="ai-badge">Anomaly</span>
                    </li>
                    <li class="list-group-item bg-dark border-secondary ai-insight fade-in" style="animation-delay: 0.4s">
                        Commercial property values in Tax Code 1054 have decreased by 2.3% despite area growth.
                        <span class="ai-badge">Anomaly</span>
                    </li>
                </ul>
            </div>
            <div class="p-3">
                <h6 class="text-muted">Recommendations</h6>
                <ul class="list-group list-group-flush">
                    <li class="list-group-item bg-dark border-secondary ai-insight fade-in" style="animation-delay: 0.6s">
                        Consider reviewing assessment methodology for commercial properties in Tax Code 1054.
                        <span class="ai-badge">Recommendation</span>
                    </li>
                    <li class="list-group-item bg-dark border-secondary ai-insight fade-in" style="animation-delay: 0.8s">
                        Prepare for increased levy capacity in School District 312 due to value growth.
                        <span class="ai-badge">Recommendation</span>
                    </li>
                </ul>
            </div>
        `;
    }, 2000);
}

/**
 * File upload functionality
 */
function setupFileUpload() {
    const fileDropAreas = document.querySelectorAll('.file-drop-area');
    
    fileDropAreas.forEach(area => {
        const input = area.querySelector('.file-drop-input');
        const fileList = area.querySelector('.upload-file-list');
        
        if (!input || !fileList) return;
        
        // Highlight drop area when dragging files over it
        ['dragenter', 'dragover'].forEach(eventName => {
            area.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            area.addEventListener(eventName, unhighlight, false);
        });
        
        // Handle dropped files
        area.addEventListener('drop', handleDrop, false);
        
        // Handle files selected via file input
        input.addEventListener('change', function() {
            handleFiles(this.files, fileList);
        });
        
        // Trigger file input click when clicking on drop area
        area.addEventListener('click', function(e) {
            if (e.target !== input && !e.target.closest('.upload-file-remove')) {
                input.click();
            }
        });
    });
    
    function highlight(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.add('highlight');
    }
    
    function unhighlight(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('highlight');
    }
    
    function handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const dt = e.dataTransfer;
        const files = dt.files;
        const fileList = this.querySelector('.upload-file-list');
        
        handleFiles(files, fileList);
    }
}

/**
 * Handle uploaded files and update UI
 */
function handleFiles(files, fileList) {
    if (!files || !fileList) return;
    
    Array.from(files).forEach(file => {
        // Create file item element
        const fileItem = document.createElement('div');
        fileItem.className = 'upload-file-item fade-in';
        
        // Determine file type icon
        let iconClass = 'bi-file-earmark';
        if (file.type.startsWith('image/')) {
            iconClass = 'bi-file-earmark-image';
        } else if (file.name.endsWith('.pdf')) {
            iconClass = 'bi-file-earmark-pdf';
        } else if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
            iconClass = 'bi-file-earmark-spreadsheet';
        } else if (file.name.endsWith('.csv')) {
            iconClass = 'bi-file-earmark-text';
        } else if (file.name.endsWith('.xml')) {
            iconClass = 'bi-file-earmark-code';
        } else if (file.name.endsWith('.txt')) {
            iconClass = 'bi-file-earmark-text';
        }
        
        fileItem.innerHTML = `
            <div class="upload-file-icon">
                <i class="bi ${iconClass}"></i>
            </div>
            <div class="upload-file-info">
                <div class="upload-file-name">${file.name}</div>
                <div class="upload-file-size">${formatFileSize(file.size)}</div>
            </div>
            <button type="button" class="upload-file-remove">
                <i class="bi bi-x"></i>
            </button>
        `;
        
        // Add remove functionality
        const removeButton = fileItem.querySelector('.upload-file-remove');
        removeButton.addEventListener('click', function(e) {
            e.stopPropagation();
            fileItem.classList.add('fade-out');
            setTimeout(() => {
                fileItem.remove();
                
                // Check if there are no more files
                if (fileList.children.length === 0) {
                    fileList.innerHTML = '';
                }
            }, 300);
        });
        
        fileList.appendChild(fileItem);
    });
}

/**
 * Format file size in a human-readable format
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Setup multiselect dropdowns
 */
function setupMultiselect() {
    const multiselects = document.querySelectorAll('.multiselect');
    
    multiselects.forEach(select => {
        const toggle = select.querySelector('.multiselect-toggle');
        const dropdown = select.querySelector('.multiselect-dropdown');
        const options = select.querySelectorAll('.multiselect-option');
        const selected = select.querySelector('.multiselect-selected');
        
        if (!toggle || !dropdown || !options.length) return;
        
        // Toggle dropdown
        toggle.addEventListener('click', function(e) {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });
        
        // Handle option selection
        options.forEach(option => {
            option.addEventListener('click', function() {
                this.classList.toggle('selected');
                updateSelectedItems(select, options, selected, toggle);
            });
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!select.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
    });
}

/**
 * Update the selected items in a multiselect
 */
function updateSelectedItems(select, options, selected, toggle) {
    if (!selected) return;
    
    // Clear current selection display
    selected.innerHTML = '';
    
    // Get selected options
    const selectedOptions = Array.from(options).filter(option => option.classList.contains('selected'));
    
    // Update toggle text
    if (selectedOptions.length === 0) {
        toggle.textContent = 'Select items';
    } else if (selectedOptions.length === 1) {
        toggle.textContent = selectedOptions[0].textContent;
    } else {
        toggle.textContent = `${selectedOptions.length} items selected`;
    }
    
    // Add badges for selected items
    selectedOptions.forEach(option => {
        const badge = document.createElement('div');
        badge.className = 'multiselect-badge';
        badge.innerHTML = `
            ${option.textContent}
            <i class="bi bi-x" data-index="${Array.from(options).indexOf(option)}"></i>
        `;
        
        // Add remove functionality
        const removeIcon = badge.querySelector('i');
        removeIcon.addEventListener('click', function(e) {
            e.stopPropagation();
            const index = this.getAttribute('data-index');
            options[index].classList.remove('selected');
            updateSelectedItems(select, options, selected, toggle);
        });
        
        selected.appendChild(badge);
    });
    
    // Update hidden input value if exists
    const hiddenInput = select.querySelector('input[type="hidden"]');
    if (hiddenInput) {
        hiddenInput.value = selectedOptions.map(option => option.getAttribute('data-value')).join(',');
    }
    
    // Trigger change event
    select.dispatchEvent(new Event('change'));
}

/**
 * Show loading overlay with message
 */
function showLoadingOverlay(message = 'Loading...') {
    // Remove existing overlay if any
    hideLoadingOverlay();
    
    // Create and add overlay
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="spinner-border loading-spinner text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <div class="mt-3 text-white">${message}</div>
    `;
    
    document.body.appendChild(overlay);
}

/**
 * Hide loading overlay
 */
function hideLoadingOverlay() {
    const existingOverlay = document.querySelector('.loading-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }
}

/**
 * Show notification toast
 */
function showNotification(message, type = 'info', duration = 3000) {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.setAttribute('id', toastId);
    
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastEl);
    
    // Initialize and show toast
    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: duration
    });
    
    toast.show();
    
    // Remove toast from DOM after it's hidden
    toastEl.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

/**
 * Format a number with commas as thousands separators and optional decimal places
 */
function formatNumber(number, decimals = 0) {
    return parseFloat(number).toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * Format a value as currency
 */
function formatCurrency(value, decimals = 2) {
    return '$' + formatNumber(value, decimals);
}

/**
 * Format a value as percentage
 */
function formatPercent(value, decimals = 1) {
    return formatNumber(value, decimals) + '%';
}