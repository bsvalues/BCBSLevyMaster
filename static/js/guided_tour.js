/**
 * Guided Tour - Tour management and UI integration for the Levy Calculation System
 * 
 * This script provides additional functionality for the guided tour system,
 * including tour navigation, tour cards, and integration with the application UI.
 */

// Tour navigation helper
class TourNavigator {
    constructor() {
        try {
            this.initUI();
            this.initEventListeners();
            console.log("Guided Tour System initialized");
        } catch (error) {
            console.error("Error initializing Guided Tour System:", error);
        }
    }
    
    // Initialize tour UI elements
    initUI() {
        // Create tour navigation element if it doesn't exist
        if (!document.getElementById('tourNavigation')) {
            const tourNav = document.createElement('div');
            tourNav.id = 'tourNavigation';
            tourNav.className = 'position-fixed bottom-0 end-0 p-3';
            tourNav.style.zIndex = '1050';
            tourNav.innerHTML = `
                <div class="card shadow-sm border-primary" style="max-width: 300px;">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">
                            <i class="bi bi-info-circle-fill me-2"></i>
                            Guided Tours
                        </h5>
                    </div>
                    <div class="card-body">
                        <p>Explore the features of our Levy Calculation System with guided tours.</p>
                        <div class="d-grid gap-2">
                            <button id="startDashboardTour" class="btn btn-outline-primary btn-sm" data-tour="dashboard">
                                <i class="bi bi-easel me-1"></i>Dashboard Tour
                            </button>
                            <button id="startCalculatorTour" class="btn btn-outline-primary btn-sm" data-tour="levy_calculator">
                                <i class="bi bi-calculator me-1"></i>Levy Calculator Tour
                            </button>
                            <a href="/tours" class="btn btn-link btn-sm text-decoration-none">
                                <i class="bi bi-list-check me-1"></i>View All Tours
                            </a>
                        </div>
                    </div>
                    <div class="card-footer bg-white d-flex justify-content-between">
                        <button id="closeTourNav" class="btn btn-sm btn-link text-muted">
                            Hide
                        </button>
                        <button id="disableTours" class="btn btn-sm btn-link text-muted">
                            Don't Show Again
                        </button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(tourNav);
        }
    }
    
    // Initialize event listeners
    initEventListeners() {
        // Event listener for closing the tour navigation
        const closeNavButton = document.getElementById('closeTourNav');
        if (closeNavButton) {
            closeNavButton.addEventListener('click', () => {
                const tourNav = document.getElementById('tourNavigation');
                if (tourNav) {
                    tourNav.style.display = 'none';
                }
            });
        }
        
        // Event listener for disabling tours
        const disableToursButton = document.getElementById('disableTours');
        if (disableToursButton) {
            disableToursButton.addEventListener('click', () => {
                localStorage.setItem('enable_auto_tours', 'false');
                const tourNav = document.getElementById('tourNavigation');
                if (tourNav) {
                    tourNav.style.display = 'none';
                }
                
                // Show confirmation toast
                this.showToast('Automatic tours have been disabled. You can re-enable them in Tour Settings.');
                
                // Update server preferences if possible
                this.updateServerPreferences();
            });
        }
        
        // Event listeners for tour buttons - using safe method
        this.safeAddEventListener('[data-tour]', 'click', function() {
            const tourName = this.getAttribute('data-tour');
            if (window.tourInitializer) {
                window.tourInitializer.startTour(tourName);
            } else {
                console.error('Tour initializer not found');
            }
        });
    }
    
    /**
     * Safe event listener addition with element existence check
     * @param {string} selector - The CSS selector for the elements
     * @param {string} event - The event to listen for
     * @param {Function} callback - The callback function
     */
    safeAddEventListener(selector, event, callback) {
        const elements = document.querySelectorAll(selector);
        if (elements && elements.length > 0) {
            elements.forEach(element => {
                element.addEventListener(event, callback);
            });
        }
    }
    
    // Show a toast notification
    showToast(message, type = 'info') {
        // Get or create toast container
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            // Create toast container if it doesn't exist
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1060';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        toastContainer.appendChild(toastEl);
        
        // Check if Bootstrap is available
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            // Initialize and show the toast
            const toast = new bootstrap.Toast(toastEl, {
                autohide: true,
                delay: 5000
            });
            toast.show();
            
            // Remove the toast after it's hidden
            toastEl.addEventListener('hidden.bs.toast', function() {
                toastEl.remove();
            });
        } else {
            // Fallback if Bootstrap isn't available
            toastEl.style.display = 'block';
            setTimeout(() => {
                toastEl.remove();
            }, 5000);
        }
    }
    
    // Update server preferences
    updateServerPreferences() {
        // Check if we have a CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (!csrfToken) {
            return;
        }
        
        // Send update to server
        fetch('/tours/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: new URLSearchParams({
                'enable_auto_tours': 'false'
            })
        })
        .catch(error => {
            console.error('Error updating tour settings:', error);
        });
    }
    
    // Show the tour helper card
    showTourHelper() {
        const tourNav = document.getElementById('tourNavigation');
        if (tourNav) {
            tourNav.style.display = 'block';
        }
    }
    
    // Hide the tour helper card
    hideTourHelper() {
        const tourNav = document.getElementById('tourNavigation');
        if (tourNav) {
            tourNav.style.display = 'none';
        }
    }
}

// Initialize tour navigator when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Check if auto tours are enabled
        const enableAutoTours = localStorage.getItem('enable_auto_tours') !== 'false';
        
        // Only show the tour helper if auto tours are enabled and user is on dashboard or main pages
        if (enableAutoTours && (
            window.location.pathname === '/dashboard' || 
            window.location.pathname === '/' ||
            window.location.pathname === '/levy-calculator'
        )) {
            window.tourNavigator = new TourNavigator();
        }
        
        // Add help button to navbar if it doesn't exist
        const navbar = document.querySelector('.navbar-nav');
        if (navbar && !document.getElementById('tourHelpButton')) {
            const helpButton = document.createElement('li');
            helpButton.className = 'nav-item';
            helpButton.innerHTML = `
                <a class="nav-link" href="/tours" id="tourHelpButton">
                    <i class="bi bi-question-circle-fill"></i>
                    <span class="ms-1 d-none d-lg-inline">Help & Tours</span>
                </a>
            `;
            navbar.appendChild(helpButton);
            console.log("Help Menu System initialized");
        }
    } catch (error) {
        console.error("Error initializing tour system:", error);
    }
});
