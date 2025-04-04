/**
 * Tour Initializer - Manages guided tours in the Levy Calculation System
 * 
 * This script initializes and manages IntroJS tours for different pages
 * of the application. It loads tour configurations and handles tour
 * completion and user preferences.
 */

// Tour configuration object
const tourConfigurations = {
    // Dashboard tour
    dashboard: {
        steps: [
            {
                element: '.dashboard-overview',
                title: 'Dashboard Overview',
                intro: 'Welcome to your dashboard! This is where you can see an overview of your tax districts, properties, and recent levy calculations.',
                position: 'right'
            },
            {
                element: '.dashboard-metrics',
                title: 'Key Metrics',
                intro: 'These cards show you the key metrics about your tax districts, such as total assessed value and levy amounts.',
                position: 'bottom'
            },
            {
                element: '.dashboard-recent-activity',
                title: 'Recent Activity',
                intro: 'Here you can see your recent activity, including imports, exports, and calculations.',
                position: 'left'
            },
            {
                element: '.dashboard-charts',
                title: 'Charts and Visualizations',
                intro: 'These charts provide visual representations of your tax data to help you identify trends and patterns.',
                position: 'top'
            },
            {
                element: '.dashboard-actions',
                title: 'Quick Actions',
                intro: 'These buttons allow you to quickly access common actions like starting a new calculation or importing data.',
                position: 'left'
            },
            {
                element: '.dashboard-notifications',
                title: 'Notifications',
                intro: 'You\'ll receive important notifications here about compliance issues, upcoming deadlines, and system updates.',
                position: 'bottom'
            }
        ]
    },
    
    // Levy calculator tour
    levy_calculator: {
        steps: [
            {
                element: '.calculator-header',
                title: 'Levy Calculator',
                intro: 'This is the levy calculator, where you can calculate property tax levies for different scenarios.',
                position: 'bottom'
            },
            {
                element: '.tax-district-selector',
                title: 'Select Tax District',
                intro: 'Start by selecting the tax district you want to calculate levies for.',
                position: 'right'
            },
            {
                element: '.calculation-inputs',
                title: 'Input Parameters',
                intro: 'Enter the required information such as year, assessed values, and rate adjustments.',
                position: 'left'
            },
            {
                element: '.scenario-options',
                title: 'Scenario Options',
                intro: 'You can create different scenarios to compare various levy outcomes.',
                position: 'top'
            },
            {
                element: '.calculate-button',
                title: 'Calculate Button',
                intro: 'Click this button to calculate the levy based on your inputs.',
                position: 'bottom'
            }
        ]
    },
    
    // Data import tour
    data_import: {
        steps: [
            {
                element: '.import-header',
                title: 'Data Import',
                intro: 'This page allows you to import tax district and property data into the system.',
                position: 'bottom'
            },
            {
                element: '.file-upload',
                title: 'File Upload',
                intro: 'You can upload files in various formats including TXT, XLS, XLSX, and XML.',
                position: 'right'
            },
            {
                element: '.import-options',
                title: 'Import Options',
                intro: 'Configure how the data should be imported with these options.',
                position: 'left'
            },
            {
                element: '.submit-import',
                title: 'Submit Import',
                intro: 'Click this button to start the import process.',
                position: 'bottom'
            }
        ]
    },
    
    // Property search tour
    property_search: {
        steps: [
            {
                element: '.search-header',
                title: 'Property Search',
                intro: 'This page allows you to search for properties in the system.',
                position: 'bottom'
            },
            {
                element: '.search-form',
                title: 'Search Criteria',
                intro: 'Enter your search criteria here to find specific properties.',
                position: 'right'
            },
            {
                element: '.search-results',
                title: 'Search Results',
                intro: 'The search results will appear here, showing matching properties.',
                position: 'top'
            },
            {
                element: '.property-details',
                title: 'Property Details',
                intro: 'Click on a property to view its detailed information.',
                position: 'left'
            }
        ]
    }
};

/**
 * Check if a tour should be automatically shown based on the current page and user preferences.
 */
function checkForAutomaticTour() {
    // Check the current path
    const path = window.location.pathname;
    
    // Check if there's a tour parameter in the URL
    const urlParams = new URLSearchParams(window.location.search);
    const tourParam = urlParams.get('tour');
    
    // If there's a tour parameter, start that tour
    if (tourParam && tourConfigurations[tourParam]) {
        startTour(tourParam);
        return;
    }
    
    // Check if auto tours are enabled
    const enableAutoTours = localStorage.getItem('enable_auto_tours') !== 'false';
    if (!enableAutoTours) {
        return;
    }
    
    // Determine which tour to show based on the current path
    let tourToShow = null;
    
    if (path === '/dashboard' || path === '/') {
        tourToShow = 'dashboard';
    } else if (path === '/levy-calculator') {
        tourToShow = 'levy_calculator';
    } else if (path === '/import') {
        tourToShow = 'data_import';
    } else if (path === '/property-lookup') {
        tourToShow = 'property_search';
    }
    
    // Start the tour if it's relevant to the current page and hasn't been completed
    if (tourToShow && !isTourCompleted(tourToShow)) {
        startTour(tourToShow);
    }
}

/**
 * Check if a tour has been completed by the user.
 * 
 * @param {string} tourName - The name of the tour to check
 * @returns {boolean} - True if the tour has been completed
 */
function isTourCompleted(tourName) {
    return localStorage.getItem(`tour_${tourName}_completed`) === 'true';
}

/**
 * Mark a tour as completed.
 * 
 * @param {string} tourName - The name of the tour to mark as completed
 */
function markTourCompleted(tourName) {
    localStorage.setItem(`tour_${tourName}_completed`, 'true');
}

/**
 * Start a guided tour.
 * 
 * @param {string} tourName - The name of the tour to start
 */
function startTour(tourName) {
    // Check if the tour exists
    if (!tourConfigurations[tourName]) {
        console.error(`Tour '${tourName}' not found`);
        return;
    }
    
    const tourConfig = tourConfigurations[tourName];
    
    // Skip if the tour has no steps
    if (!tourConfig.steps || tourConfig.steps.length === 0) {
        console.error(`Tour '${tourName}' has no steps`);
        return;
    }
    
    // Initialize introjs with the tour configuration
    const intro = introJs();
    
    // Configure the tour
    intro.setOptions({
        steps: tourConfig.steps,
        showProgress: localStorage.getItem('show_progress_bar') !== 'false',
        showBullets: localStorage.getItem('show_bullets') !== 'false',
        exitOnOverlayClick: localStorage.getItem('exit_on_overlay_click') !== 'false',
        scrollToElement: localStorage.getItem('scroll_to_element') !== 'false',
        doneLabel: 'Finish',
        nextLabel: 'Next →',
        prevLabel: '← Back',
        skipLabel: 'Skip'
    });
    
    // Add event listeners
    intro.oncomplete(function() {
        // Mark the tour as completed when the user finishes it
        markTourCompleted(tourName);
    });
    
    intro.onexit(function() {
        // Don't mark as completed if user exits early
    });
    
    // Start the tour
    intro.start();
}

// Initialize when the DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if we need to automatically start a tour
    checkForAutomaticTour();
    
    // Add event listeners to tour trigger buttons
    document.querySelectorAll('[data-tour]').forEach(button => {
        button.addEventListener('click', function() {
            const tourName = this.getAttribute('data-tour');
            startTour(tourName);
        });
    });
});

// Export functions for use in other scripts
window.tourInitializer = {
    startTour: startTour,
    checkForAutomaticTour: checkForAutomaticTour,
    isTourCompleted: isTourCompleted,
    markTourCompleted: markTourCompleted
};
