/**
 * Levy Calculation System - Custom JavaScript
 */

// Constants
const DEBOUNCE_DELAY = 300; // Milliseconds to wait before executing debounced functions

/**
 * Debounce function to limit how often a function can be called
 * @param {Function} func - The function to debounce
 * @param {number} wait - The delay in milliseconds (default: 300)
 * @returns {Function} - Debounced function
 */
function debounce(func, wait = DEBOUNCE_DELAY) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

/**
 * Format a number as currency
 * @param {number} value - The number to format
 * @param {string} locale - The locale to use (default: 'en-US')
 * @param {string} currency - The currency code (default: 'USD')
 * @returns {string} - Formatted currency string
 */
function formatCurrency(value, locale = 'en-US', currency = 'USD') {
    if (value === null || value === undefined) return '-';
    return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency
    }).format(value);
}

/**
 * Format a number with thousand separators
 * @param {number} value - The number to format
 * @param {number} decimals - The number of decimal places (default: 2)
 * @returns {string} - Formatted number string
 */
function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined) return '-';
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(value);
}

/**
 * Format a number as a percentage
 * @param {number} value - The decimal value to format as percentage
 * @param {number} decimals - The number of decimal places (default: 2)
 * @returns {string} - Formatted percentage string
 */
function formatPercentage(value, decimals = 2) {
    if (value === null || value === undefined) return '-';
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(value);
}

/**
 * Create a loading spinner overlay
 * @param {string} containerId - The ID of the container element (default: 'body')
 * @param {string} message - Optional message to display with the spinner
 * @returns {HTMLElement} - The spinner element
 */
function createLoadingSpinner(containerId = 'body', message = 'Loading...') {
    const container = document.getElementById(containerId) || document.body;
    const spinnerOverlay = document.createElement('div');
    spinnerOverlay.className = 'spinner-overlay';
    spinnerOverlay.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <div class="spinner-message">${message}</div>
    `;
    
    // Apply relative positioning to container if not already positioned
    if (getComputedStyle(container).position === 'static') {
        container.style.position = 'relative';
    }
    
    container.appendChild(spinnerOverlay);
    return spinnerOverlay;
}

/**
 * Remove loading spinner
 * @param {HTMLElement} spinnerElement - The spinner element to remove
 */
function removeLoadingSpinner(spinnerElement) {
    if (spinnerElement && spinnerElement.parentNode) {
        spinnerElement.parentNode.removeChild(spinnerElement);
    }
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, error, warning, info)
 * @param {number} duration - How long to show the toast in ms (default: 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
    const container = document.querySelector('.toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center border-0 bg-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    // Set toast content
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body text-white">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Initialize toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: duration
    });
    
    bsToast.show();
    
    // Remove toast from DOM after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

/**
 * Ajax utility function to make API requests
 * @param {string} url - The URL to send the request to
 * @param {Object} options - Request options (method, data, headers, etc.)
 * @returns {Promise} - Promise that resolves with the response data
 */
async function makeRequest(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    };
    
    // Add CSRF token if available
    const csrfToken = getCsrfToken();
    if (csrfToken) {
        defaultOptions.headers['X-CSRFToken'] = csrfToken;
    }
    
    // Merge default options with provided options
    const requestOptions = { ...defaultOptions, ...options };
    
    // Convert data to JSON string if it's an object and not already handled
    if (requestOptions.data && typeof requestOptions.data === 'object' && !(requestOptions.data instanceof FormData)) {
        requestOptions.body = JSON.stringify(requestOptions.data);
        delete requestOptions.data;
    } else if (requestOptions.data instanceof FormData) {
        requestOptions.body = requestOptions.data;
        delete requestOptions.data;
        delete requestOptions.headers['Content-Type']; // Let browser set content type with boundary
    }
    
    try {
        const response = await fetch(url, requestOptions);
        
        // Parse response based on content type
        const contentType = response.headers.get('content-type');
        let data;
        
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            data = await response.text();
        }
        
        // Handle error responses
        if (!response.ok) {
            const error = new Error(data.message || response.statusText);
            error.response = response;
            error.data = data;
            throw error;
        }
        
        return data;
    } catch (error) {
        console.error('Request error:', error);
        throw error;
    }
}

/**
 * Copy text to clipboard
 * @param {string} text - The text to copy
 * @returns {Promise<boolean>} - Whether the operation was successful
 */
async function copyToClipboard(text) {
    if (!navigator.clipboard) {
        fallbackCopyToClipboard(text);
        return true;
    }
    
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (error) {
        console.error('Could not copy text to clipboard', error);
        return false;
    }
}

/**
 * Fallback method to copy to clipboard
 * @param {string} text - The text to copy
 * @returns {boolean} - Whether the operation was successful
 */
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    
    // Make the textarea out of viewport
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    let success = false;
    try {
        success = document.execCommand('copy');
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
    }
    
    document.body.removeChild(textArea);
    return success;
}

/**
 * Get CSRF token from meta tag
 * @returns {string|null} - The CSRF token or null if not found
 */
function getCsrfToken() {
    const tokenElement = document.querySelector('meta[name="csrf-token"]');
    return tokenElement ? tokenElement.getAttribute('content') : null;
}

/**
 * Confirm action with a Bootstrap modal
 * @param {string} message - The confirmation message
 * @param {Function} onConfirm - Callback function to execute on confirmation
 * @param {string} title - The modal title (default: 'Confirm Action')
 */
function confirmAction(message, onConfirm, title = 'Confirm Action') {
    const modal = document.getElementById('confirmActionModal');
    if (!modal) return;
    
    const modalTitle = modal.querySelector('.modal-title');
    const modalBody = modal.querySelector('.modal-body');
    const confirmButton = document.getElementById('confirmActionButton');
    
    modalTitle.textContent = title;
    modalBody.textContent = message;
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    // Remove any existing event listeners
    const newConfirmButton = confirmButton.cloneNode(true);
    confirmButton.parentNode.replaceChild(newConfirmButton, confirmButton);
    
    // Add event listener for confirmation
    newConfirmButton.addEventListener('click', function() {
        bsModal.hide();
        if (typeof onConfirm === 'function') {
            onConfirm();
        }
    });
}

/**
 * Initialize tooltip elements on the page
 */
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
}

/**
 * Initialize popover elements on the page
 */
function initPopovers() {
    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    popovers.forEach(popover => {
        new bootstrap.Popover(popover);
    });
}

/**
 * Initialize data tables with common settings
 * @param {string} tableId - The ID of the table element
 * @param {Object} options - DataTable options
 * @returns {Object} - The initialized DataTable instance
 */
function initDataTable(tableId, options = {}) {
    const defaultOptions = {
        responsive: true,
        lengthMenu: [10, 25, 50, 100],
        pageLength: 25,
        language: {
            search: '_INPUT_',
            searchPlaceholder: 'Search...',
            lengthMenu: 'Show _MENU_ entries per page',
            info: 'Showing _START_ to _END_ of _TOTAL_ entries',
            emptyTable: 'No data available'
        },
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        drawCallback: function() {
            // Re-initialize tooltips in the table
            initTooltips();
        }
    };
    
    // Merge default options with provided options
    const tableOptions = { ...defaultOptions, ...options };
    
    // Initialize DataTable
    if (typeof $.fn.DataTable !== 'undefined') {
        return $('#' + tableId).DataTable(tableOptions);
    } else {
        console.error('DataTables library not loaded');
        return null;
    }
}

/**
 * Format a date string in a localized format
 * @param {string|Date} dateValue - The date to format
 * @param {string} locale - The locale to use (default: 'en-US')
 * @param {Object} options - The date format options
 * @returns {string} - Formatted date string
 */
function formatDate(dateValue, locale = 'en-US', options = {}) {
    if (!dateValue) return '-';
    
    const defaultOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    };
    
    const dateOptions = { ...defaultOptions, ...options };
    
    // Convert string to Date object if necessary
    const date = typeof dateValue === 'string' ? new Date(dateValue) : dateValue;
    
    // Check if date is valid
    if (isNaN(date.getTime())) return 'Invalid date';
    
    return new Intl.DateTimeFormat(locale, dateOptions).format(date);
}

/**
 * Add event listener to elements matching a selector
 * @param {string} selector - CSS selector for elements
 * @param {string} eventType - Type of event to listen for
 * @param {Function} handler - Event handler function
 */
function addEventListenerToElements(selector, eventType, handler) {
    document.querySelectorAll(selector).forEach(element => {
        element.addEventListener(eventType, handler);
    });
}

/**
 * Handle form submissions with Ajax
 * @param {string} formId - The ID of the form element
 * @param {Function} onSuccess - Callback function on successful submission
 * @param {Function} onError - Callback function on error
 */
function handleAjaxForm(formId, onSuccess, onError) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    form.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        // Show loading spinner
        const spinner = createLoadingSpinner(formId, 'Submitting...');
        
        try {
            const formData = new FormData(form);
            const url = form.getAttribute('action') || window.location.href;
            const method = form.getAttribute('method') || 'POST';
            
            const response = await makeRequest(url, {
                method: method,
                data: formData
            });
            
            // Call success callback
            if (typeof onSuccess === 'function') {
                onSuccess(response);
            } else {
                // Default success behavior
                showToast('Form submitted successfully', 'success');
                
                // Reset form if no success callback provided
                form.reset();
            }
        } catch (error) {
            // Call error callback
            if (typeof onError === 'function') {
                onError(error);
            } else {
                // Default error behavior
                const errorMessage = error.data && error.data.message 
                    ? error.data.message 
                    : 'An error occurred while submitting the form';
                
                showToast(errorMessage, 'danger');
                console.error('Form submission error:', error);
            }
        } finally {
            // Remove loading spinner
            removeLoadingSpinner(spinner);
        }
    });
}

/**
 * Initialize file input customization
 */
function initFileInputs() {
    document.querySelectorAll('.custom-file-input').forEach(input => {
        input.addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name || 'No file chosen';
            const label = e.target.nextElementSibling;
            if (label) {
                label.textContent = fileName;
            }
        });
    });
}

/**
 * Handle dark mode toggle
 */
function initDarkModeToggle() {
    const toggle = document.getElementById('darkModeToggle');
    if (!toggle) return;
    
    toggle.addEventListener('click', function() {
        const html = document.documentElement;
        if (html.getAttribute('data-bs-theme') === 'dark') {
            html.setAttribute('data-bs-theme', 'light');
            localStorage.setItem('theme', 'light');
        } else {
            html.setAttribute('data-bs-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        }
        
        // Update charts if any
        updateChartsTheme();
    });
    
    // Set initial theme based on stored preference
    const storedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-bs-theme', storedTheme);
}

/**
 * Initialize glossary term tooltips
 */
function initGlossaryTerms() {
    const terms = document.querySelectorAll('.glossary-term');
    terms.forEach(term => {
        new bootstrap.Tooltip(term, {
            html: true,
            template: '<div class="tooltip glossary-tooltip" role="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner bg-info"></div></div>',
            placement: 'top',
            boundary: 'window'
        });
    });
}

/**
 * Generic function to create a Chart.js chart
 * @param {string} canvasId - The ID of the canvas element
 * @param {string} type - The type of chart (line, bar, pie, etc.)
 * @param {Object} data - The chart data
 * @param {Object} options - Chart options
 * @returns {Object} - The Chart.js instance
 */
function createChart(canvasId, type, data, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return null;
    
    // Default chart options
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: '#e0e0e0'
                }
            },
            tooltip: {
                mode: 'index',
                intersect: false
            }
        },
        scales: {
            x: {
                ticks: {
                    color: '#e0e0e0'
                },
                grid: {
                    color: 'rgba(255, 255, 255, 0.1)'
                }
            },
            y: {
                ticks: {
                    color: '#e0e0e0'
                },
                grid: {
                    color: 'rgba(255, 255, 255, 0.1)'
                }
            }
        }
    };
    
    // Merge default options with provided options
    const chartOptions = { ...defaultOptions, ...options };
    
    // Create and return the chart
    return new Chart(canvas.getContext('2d'), {
        type: type,
        data: data,
        options: chartOptions
    });
}

/**
 * Update chart data and options
 * @param {Object} chart - The Chart.js instance
 * @param {Object} newData - New data for the chart
 * @param {Object} newOptions - New options for the chart
 */
function updateChart(chart, newData, newOptions = {}) {
    if (!chart) return;
    
    // Update data
    if (newData) {
        chart.data = newData;
    }
    
    // Update options
    if (newOptions && Object.keys(newOptions).length > 0) {
        chart.options = { ...chart.options, ...newOptions };
    }
    
    // Update chart
    chart.update();
}

/**
 * Adjust chart theme based on current theme
 * @param {Object} chart - The Chart.js instance
 */
function updateChartTheme(chart) {
    if (!chart) return;
    
    const isDarkMode = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    
    // Update text colors
    chart.options.scales.x.ticks.color = isDarkMode ? '#e0e0e0' : '#666';
    chart.options.scales.y.ticks.color = isDarkMode ? '#e0e0e0' : '#666';
    chart.options.plugins.legend.labels.color = isDarkMode ? '#e0e0e0' : '#666';
    
    // Update grid colors
    chart.options.scales.x.grid.color = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    chart.options.scales.y.grid.color = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    // Update chart
    chart.update();
}

/**
 * Listen for theme changes to update charts
 */
function updateChartsTheme() {
    // Find all charts in the registry
    if (typeof Chart !== 'undefined' && Chart.instances) {
        Object.values(Chart.instances).forEach(chart => {
            updateChartTheme(chart);
        });
    }
}

/**
 * Levy-specific: Format levy rates for display
 * @param {number} rate - The levy rate value (e.g., 0.00152)
 * @returns {string} - Formatted levy rate (e.g., $1.52 per $1,000)
 */
function formatLevyRate(rate) {
    if (rate === null || rate === undefined) return '-';
    // Multiply by 1000 to show as rate per $1,000
    const ratePerThousand = rate * 1000;
    return `$${formatNumber(ratePerThousand)} per $1,000`;
}

/**
 * Levy-specific: Calculate levy amount based on rate and assessed value
 * @param {number} rate - The levy rate (e.g., 0.00152)
 * @param {number} assessedValue - The assessed value
 * @returns {number} - The calculated levy amount
 */
function calculateLevyAmount(rate, assessedValue) {
    if (rate === null || assessedValue === null) return null;
    return rate * assessedValue;
}

/**
 * Levy-specific: Calculate levy rate based on levy amount and assessed value
 * @param {number} levyAmount - The levy amount
 * @param {number} assessedValue - The assessed value
 * @returns {number} - The calculated levy rate
 */
function calculateLevyRate(levyAmount, assessedValue) {
    if (levyAmount === null || assessedValue === null || assessedValue === 0) return null;
    return levyAmount / assessedValue;
}

/**
 * Levy-specific: Calculate percentage change between two values
 * @param {number} newValue - The new value
 * @param {number} oldValue - The old value
 * @returns {number} - The percentage change
 */
function calculatePercentageChange(newValue, oldValue) {
    if (oldValue === 0 || oldValue === null || oldValue === undefined) return null;
    return (newValue - oldValue) / oldValue;
}

/**
 * Levy-specific: Generate a color based on the trend direction
 * @param {number} value - The percentage change value
 * @param {boolean} invertColors - Whether to invert color mapping (default: false)
 * @returns {string} - CSS color value
 */
function getTrendColor(value, invertColors = false) {
    if (value === null || value === undefined) return '#6c757d'; // Secondary color for null
    
    // Determine if positive trend is good (green) or bad (red)
    const isPositiveGood = !invertColors;
    
    if (value > 0) {
        return isPositiveGood ? '#198754' : '#dc3545'; // Success or danger
    } else if (value < 0) {
        return isPositiveGood ? '#dc3545' : '#198754'; // Danger or success
    } else {
        return '#6c757d'; // Secondary color for zero change
    }
}

// Initialize components on document load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize file inputs
    initFileInputs();
    
    // Initialize dark mode toggle
    initDarkModeToggle();
    
    // Enable copy to clipboard buttons
    addEventListenerToElements('.btn-copy', 'click', function(e) {
        const text = this.dataset.copyText || '';
        if (text) {
            copyToClipboard(text).then(success => {
                if (success) {
                    showToast('Copied to clipboard!', 'success', 1500);
                }
            });
        }
    });
    
    // Initialize any Ajax forms
    document.querySelectorAll('form[data-ajax="true"]').forEach(form => {
        const formId = form.id;
        const successUrl = form.dataset.successUrl;
        
        handleAjaxForm(formId, 
            // Success callback
            function(response) {
                showToast(response.message || 'Form submitted successfully', 'success');
                
                // Redirect if success URL is provided
                if (successUrl) {
                    setTimeout(() => {
                        window.location.href = successUrl;
                    }, 1000);
                }
            },
            // Error callback
            function(error) {
                const errorMessage = error.data && error.data.message 
                    ? error.data.message 
                    : 'An error occurred while submitting the form';
                
                showToast(errorMessage, 'danger');
                
                // If there are field-specific errors, highlight them
                if (error.data && error.data.errors) {
                    Object.keys(error.data.errors).forEach(field => {
                        const input = document.querySelector(`#${formId} [name="${field}"]`);
                        if (input) {
                            input.classList.add('is-invalid');
                            
                            // Create or update the error message
                            let feedback = input.nextElementSibling;
                            if (!feedback || !feedback.classList.contains('invalid-feedback')) {
                                feedback = document.createElement('div');
                                feedback.className = 'invalid-feedback';
                                input.parentNode.insertBefore(feedback, input.nextSibling);
                            }
                            
                            feedback.textContent = error.data.errors[field][0];
                        }
                    });
                }
            }
        );
    });
});