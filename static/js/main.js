/**
 * Main JavaScript file for the SaaS Levy Calculation Application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-persistent)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Enhance custom file input labels
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        const label = input.nextElementSibling;
        
        if (label && label.classList.contains('custom-file-label')) {
            input.addEventListener('change', function(e) {
                const fileName = e.target.files[0].name;
                label.textContent = fileName;
            });
        }
    });

    // Add active class to current nav item
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(function(link) {
        const href = link.getAttribute('href');
        if (href === currentPath || 
            (href !== '/' && currentPath.startsWith(href))) {
            link.classList.add('active');
        }
    });

    // Format currency inputs
    const currencyInputs = document.querySelectorAll('.currency-input');
    currencyInputs.forEach(function(input) {
        input.addEventListener('blur', function(e) {
            const value = parseFloat(e.target.value.replace(/[^\d.-]/g, ''));
            if (!isNaN(value)) {
                e.target.value = value.toLocaleString('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    minimumFractionDigits: 2
                });
            }
        });
        
        input.addEventListener('focus', function(e) {
            e.target.value = e.target.value.replace(/[^\d.-]/g, '');
        });
    });
    
    // Setup confirmation modals
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm(button.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });
    
    // Enable dynamic form fields
    const addFieldButtons = document.querySelectorAll('.add-field');
    addFieldButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const container = document.querySelector(button.dataset.container);
            const template = document.querySelector(button.dataset.template);
            
            if (container && template) {
                const clone = template.content.cloneNode(true);
                container.appendChild(clone);
                
                // Initialize any dynamic elements in the clone
                const newField = container.lastElementChild;
                if (newField) {
                    const removeButton = newField.querySelector('.remove-field');
                    if (removeButton) {
                        removeButton.addEventListener('click', function() {
                            newField.remove();
                        });
                    }
                }
            }
        });
    });
});