/**
 * Levy Calculation System - Main JavaScript
 */

// Wait for DOM content to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    
    // Handle dark mode toggle
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            const htmlElement = document.documentElement;
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            
            // Toggle theme
            if (currentTheme === 'dark') {
                htmlElement.setAttribute('data-bs-theme', 'light');
                this.innerHTML = '<i class="bi bi-sun-fill"></i>';
                localStorage.setItem('theme', 'light');
            } else {
                htmlElement.setAttribute('data-bs-theme', 'dark');
                this.innerHTML = '<i class="bi bi-moon-fill"></i>';
                localStorage.setItem('theme', 'dark');
            }
        });
        
        // Set theme based on user preference from localStorage
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-bs-theme', savedTheme);
            darkModeToggle.innerHTML = savedTheme === 'dark' 
                ? '<i class="bi bi-moon-fill"></i>' 
                : '<i class="bi bi-sun-fill"></i>';
        }
    }
    
    // Enable bootstrap tooltips everywhere
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    const autoAlerts = document.querySelectorAll('.alert-auto-dismiss');
    autoAlerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Add animation classes to elements with data-animate attribute
    const animateElements = document.querySelectorAll('[data-animate]');
    animateElements.forEach(function(element) {
        const animationClass = element.getAttribute('data-animate');
        element.classList.add(animationClass);
    });
    
    // Handle form validation styling
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    console.log('Levy Calculation System JS initialized successfully');
});