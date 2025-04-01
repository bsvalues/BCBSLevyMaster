/**
 * Main JavaScript for Levy Calculation System
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initComponents();
    
    // Handle year selector
    initYearSelector();
    
    // Initialize data tables
    initDataTables();
    
    // Initialize auto-dismiss alerts
    initAutoDismissAlerts();
    
    // Initialize animations
    initCardAnimations();
    
    // Handle file uploads if upload zone exists
    initFileUpload();
});

/**
 * Initialize all components and UI elements
 */
function initComponents() {
    // Initialize tooltips
    initTooltips();
    
    // Initialize popovers
    initPopovers();
}

/**
 * Initialize Bootstrap tooltips
 */
function initTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl, {
        boundary: document.body
    }));
}

/**
 * Initialize Bootstrap popovers
 */
function initPopovers() {
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl, {
        html: true,
        sanitize: false,
        container: 'body'
    }));
}

/**
 * Initialize file upload functionality with drag and drop support
 */
function initFileUpload() {
    const uploadZones = document.querySelectorAll('.upload-zone');
    
    uploadZones.forEach(zone => {
        const input = zone.querySelector('input[type="file"]');
        const preview = zone.querySelector('.file-preview');
        
        if (!input) return;
        
        // Handle click to select files
        zone.addEventListener('click', () => {
            input.click();
        });
        
        // Handle file selection
        input.addEventListener('change', () => {
            updateFileDisplay(input.files, preview);
        });
        
        // Handle drag and drop
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });
        
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('drag-over');
        });
        
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            
            // Get the dropped files
            const files = e.dataTransfer.files;
            
            // Set the files on the input
            if (files.length > 0) {
                input.files = files;
                updateFileDisplay(files, preview);
            }
        });
    });
}

/**
 * Update file display in the upload zone
 * @param {FileList} files - The selected files
 * @param {HTMLElement} preview - The preview element
 */
function updateFileDisplay(files, preview) {
    if (!preview) return;
    
    preview.innerHTML = '';
    
    if (files.length > 0) {
        const fileList = document.createElement('ul');
        fileList.className = 'list-group mt-3';
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const item = document.createElement('li');
            item.className = 'list-group-item d-flex justify-content-between align-items-center';
            
            // Get file icon based on type
            let icon = 'bi-file-earmark';
            if (file.type.includes('excel') || file.name.endsWith('.xls') || file.name.endsWith('.xlsx')) {
                icon = 'bi-file-earmark-excel';
            } else if (file.type.includes('csv') || file.name.endsWith('.csv')) {
                icon = 'bi-file-earmark-spreadsheet';
            } else if (file.type.includes('xml') || file.name.endsWith('.xml')) {
                icon = 'bi-file-earmark-code';
            } else if (file.type.includes('text') || file.name.endsWith('.txt')) {
                icon = 'bi-file-earmark-text';
            }
            
            item.innerHTML = `
                <div>
                    <i class="bi ${icon} me-2"></i>
                    ${file.name}
                </div>
                <span class="badge bg-secondary rounded-pill">${formatFileSize(file.size)}</span>
            `;
            
            fileList.appendChild(item);
        }
        
        preview.appendChild(fileList);
    }
}

/**
 * Format file size in human-readable format
 * @param {number} bytes - The file size in bytes
 * @returns {string} - Formatted file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Initialize year selector in navigation
 */
function initYearSelector() {
    const yearLinks = document.querySelectorAll('.year-selector .dropdown-item');
    const yearForm = document.getElementById('yearForm');
    const yearInput = yearForm ? yearForm.querySelector('input[name="selected_year"]') : null;
    const yearButton = document.getElementById('yearSelector');
    
    if (!yearLinks.length || !yearForm || !yearInput || !yearButton) return;
    
    yearLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const year = link.getAttribute('data-year');
            
            // Update form input and submit
            yearInput.value = year;
            yearButton.textContent = year;
            yearForm.submit();
        });
    });
}

/**
 * Initialize search functionality
 */
function initSearch() {
    const searchInputs = document.querySelectorAll('.search-input');
    
    searchInputs.forEach(input => {
        const targetTable = document.querySelector(input.getAttribute('data-target'));
        
        if (!targetTable) return;
        
        input.addEventListener('keyup', () => {
            const query = input.value.toLowerCase().trim();
            filterTable(targetTable, query);
        });
    });
}

/**
 * Filter table rows based on search query
 * @param {HTMLElement} table - The table to filter
 * @param {string} query - The search query
 */
function filterTable(table, query) {
    const rows = table.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
    });
    
    // Update "no results" message if needed
    const noResults = table.nextElementSibling;
    if (noResults && noResults.classList.contains('no-results')) {
        const visibleRows = table.querySelectorAll('tbody tr[style=""]').length;
        noResults.style.display = visibleRows === 0 ? 'block' : 'none';
    }
}

/**
 * Initialize data tables with sorting and pagination
 */
function initDataTables() {
    const tables = document.querySelectorAll('.data-table');
    
    tables.forEach(table => {
        // Add click handlers for sorting
        const headers = table.querySelectorAll('th[data-sort]');
        
        headers.forEach(header => {
            header.addEventListener('click', () => {
                const sortType = header.getAttribute('data-sort');
                const columnIndex = Array.from(header.parentNode.children).indexOf(header);
                const isAscending = !header.classList.contains('sort-asc');
                
                // Remove sort classes from all headers
                headers.forEach(h => {
                    h.classList.remove('sort-asc', 'sort-desc');
                });
                
                // Add sort class to the clicked header
                header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
                
                // Sort the table
                sortTable(table, columnIndex, sortType, isAscending);
            });
        });
        
        // Initialize pagination if needed
        const paginationContainer = table.nextElementSibling;
        if (paginationContainer && paginationContainer.classList.contains('pagination-container')) {
            const rowsPerPage = parseInt(table.getAttribute('data-rows-per-page')) || 10;
            initPagination(table, paginationContainer, rowsPerPage);
        }
    });
    
    // Initialize search functionality
    initSearch();
}

/**
 * Initialize pagination for a table
 * @param {HTMLElement} table - The table to paginate
 * @param {HTMLElement} container - The pagination container
 * @param {number} rowsPerPage - Number of rows per page
 */
function initPagination(table, container, rowsPerPage = 10) {
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    const totalPages = Math.ceil(rows.length / rowsPerPage);
    
    // Hide all rows initially
    rows.forEach((row, index) => {
        row.classList.add('paginated-row');
        row.setAttribute('data-page', Math.floor(index / rowsPerPage) + 1);
    });
    
    // Show first page
    showPage(table, 1, rowsPerPage);
    
    // Create pagination controls
    const paginationElement = document.createElement('ul');
    paginationElement.className = 'pagination pagination-sm justify-content-center mt-3 mb-0';
    
    // Previous button
    const prevItem = document.createElement('li');
    prevItem.className = 'page-item prev-page disabled';
    prevItem.innerHTML = '<a class="page-link" href="#"><i class="bi bi-chevron-left"></i></a>';
    paginationElement.appendChild(prevItem);
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        const pageItem = document.createElement('li');
        pageItem.className = `page-item page-number ${i === 1 ? 'active' : ''}`;
        pageItem.innerHTML = `<a class="page-link" href="#">${i}</a>`;
        paginationElement.appendChild(pageItem);
    }
    
    // Next button
    const nextItem = document.createElement('li');
    nextItem.className = 'page-item next-page';
    nextItem.innerHTML = '<a class="page-link" href="#"><i class="bi bi-chevron-right"></i></a>';
    paginationElement.appendChild(nextItem);
    
    container.innerHTML = '';
    container.appendChild(paginationElement);
    
    // Add event listeners
    const pageLinks = container.querySelectorAll('.page-number');
    pageLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const pageNumber = parseInt(link.querySelector('a').textContent);
            changePage(table, container, pageNumber, rowsPerPage);
        });
    });
    
    prevItem.addEventListener('click', (e) => {
        e.preventDefault();
        if (prevItem.classList.contains('disabled')) return;
        
        const activePage = container.querySelector('.page-number.active');
        const pageNumber = parseInt(activePage.querySelector('a').textContent) - 1;
        changePage(table, container, pageNumber, rowsPerPage);
    });
    
    nextItem.addEventListener('click', (e) => {
        e.preventDefault();
        if (nextItem.classList.contains('disabled')) return;
        
        const activePage = container.querySelector('.page-number.active');
        const pageNumber = parseInt(activePage.querySelector('a').textContent) + 1;
        changePage(table, container, pageNumber, rowsPerPage);
    });
}

/**
 * Show a specific page of a paginated table
 * @param {HTMLElement} table - The table element
 * @param {number} page - The page number to show
 * @param {number} rowsPerPage - The number of rows per page
 */
function showPage(table, page, rowsPerPage) {
    const rows = table.querySelectorAll('tbody tr.paginated-row');
    
    rows.forEach(row => {
        const rowPage = parseInt(row.getAttribute('data-page'));
        row.style.display = rowPage === page ? '' : 'none';
    });
}

/**
 * Change the current page of a paginated table
 * @param {HTMLElement} table - The table element
 * @param {HTMLElement} pagination - The pagination container
 * @param {number} page - The page number to change to
 * @param {number} rowsPerPage - The number of rows per page
 */
function changePage(table, pagination, page, rowsPerPage) {
    showPage(table, page, rowsPerPage);
    
    // Update active page
    const pageItems = pagination.querySelectorAll('.page-number');
    pageItems.forEach(item => {
        const itemPage = parseInt(item.querySelector('a').textContent);
        item.classList.toggle('active', itemPage === page);
    });
    
    // Update prev/next buttons
    const totalPages = pageItems.length;
    pagination.querySelector('.prev-page').classList.toggle('disabled', page === 1);
    pagination.querySelector('.next-page').classList.toggle('disabled', page === totalPages);
}

/**
 * Sort a table by a specific column
 * @param {HTMLElement} table - The table to sort
 * @param {number} columnIndex - The index of the column to sort by
 * @param {string} type - The type of data in the column (text, number, date)
 * @param {boolean} ascending - Whether to sort in ascending order
 */
function sortTable(table, columnIndex, type, ascending) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Sort the rows
    rows.sort((a, b) => {
        const cellA = a.cells[columnIndex].textContent.trim();
        const cellB = b.cells[columnIndex].textContent.trim();
        
        let comparison = 0;
        
        if (type === 'number') {
            // Extract numeric values and compare
            const numA = parseFloat(cellA.replace(/[^0-9.-]+/g, ''));
            const numB = parseFloat(cellB.replace(/[^0-9.-]+/g, ''));
            comparison = numA - numB;
        } else if (type === 'date') {
            // Convert to dates and compare
            const dateA = new Date(cellA);
            const dateB = new Date(cellB);
            comparison = dateA - dateB;
        } else {
            // Default string comparison
            comparison = cellA.localeCompare(cellB);
        }
        
        return ascending ? comparison : -comparison;
    });
    
    // Reorder the rows in the table
    rows.forEach(row => {
        tbody.appendChild(row);
    });
    
    // Update pagination if needed
    if (table.classList.contains('paginated')) {
        const paginationContainer = table.nextElementSibling;
        if (paginationContainer && paginationContainer.classList.contains('pagination-container')) {
            const activePage = paginationContainer.querySelector('.page-number.active');
            if (activePage) {
                const page = parseInt(activePage.querySelector('a').textContent);
                const rowsPerPage = parseInt(table.getAttribute('data-rows-per-page')) || 10;
                
                // Re-assign page numbers to rows
                rows.forEach((row, index) => {
                    row.setAttribute('data-page', Math.floor(index / rowsPerPage) + 1);
                });
                
                showPage(table, page, rowsPerPage);
            }
        }
    }
}

/**
 * Initialize auto-dismissing alerts
 */
function initAutoDismissAlerts() {
    const autoDismissAlerts = document.querySelectorAll('.alert.auto-dismiss');
    
    autoDismissAlerts.forEach(alert => {
        const dismissDelay = alert.getAttribute('data-dismiss-delay') || 5000;
        
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, dismissDelay);
    });
}

/**
 * Initialize card animations
 */
function initCardAnimations() {
    const fadeElements = document.querySelectorAll('.fade-in');
    
    // Ensure elements are visible after animation
    fadeElements.forEach(element => {
        element.style.opacity = '1';
    });
}

/**
 * Format a number with commas as thousands separators
 * @param {number} value - The number to format
 * @returns {string} - Formatted number
 */
function formatNumber(value) {
    return new Intl.NumberFormat().format(value);
}

/**
 * Format a currency value with dollar sign and commas
 * @param {number} value - The value to format
 * @returns {string} - Formatted currency
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(value);
}

/**
 * Format a percentage value with percent sign
 * @param {number} value - The value to format (e.g., 0.15 for 15%)
 * @returns {string} - Formatted percentage
 */
function formatPercent(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

/**
 * Confirm user action with a custom confirmation modal
 * @param {string} message - The confirmation message
 * @param {Function} callback - The function to call if confirmed
 */
function confirmAction(message, callback) {
    const existingModal = document.getElementById('confirmationModal');
    
    // Remove existing modal if any
    if (existingModal) {
        existingModal.remove();
    }
    
    // Create the modal
    const modalHTML = `
        <div class="modal fade" id="confirmationModal" tabindex="-1" aria-labelledby="confirmationModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="confirmationModalLabel">Confirm Action</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        ${message}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="confirmButton">Confirm</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Append the modal to the body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Get the modal element
    const modalElement = document.getElementById('confirmationModal');
    
    // Initialize the modal
    const modal = new bootstrap.Modal(modalElement);
    
    // Add event listener to the confirm button
    document.getElementById('confirmButton').addEventListener('click', () => {
        modal.hide();
        callback();
    });
    
    // Show the modal
    modal.show();
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, error, warning, info)
 */
function showToast(message, type = 'success') {
    // Map type to Bootstrap class and icon
    const typeMap = {
        success: { class: 'bg-success', icon: 'bi-check-circle' },
        error: { class: 'bg-danger', icon: 'bi-exclamation-circle' },
        warning: { class: 'bg-warning', icon: 'bi-exclamation-triangle' },
        info: { class: 'bg-info', icon: 'bi-info-circle' }
    };
    
    const typeInfo = typeMap[type] || typeMap.info;
    
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast
    const toastId = 'toast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header ${typeInfo.class} text-white">
                <i class="bi ${typeInfo.icon} me-2"></i>
                <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                <small>Just now</small>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // Add toast to container
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    
    // Show the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
    toast.show();
    
    // Remove toast from DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}