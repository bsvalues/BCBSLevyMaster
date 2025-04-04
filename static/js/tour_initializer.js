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
                element: '.quick-stats',
                title: 'Key Metrics',
                intro: 'These cards show your key metrics at a glance, including total properties, tax districts, and recent calculations.',
                position: 'bottom'
            },
            {
                element: '.recent-activity',
                title: 'Recent Activity',
                intro: 'This section shows your recent activity, including imports, exports, and calculations.',
                position: 'left'
            },
            {
                element: '.tax-district-summary',
                title: 'Tax District Summary',
                intro: 'View a summary of your tax districts, including total assessed value and levy amounts.',
                position: 'top'
            },
            {
                element: '.action-buttons',
                title: 'Quick Actions',
                intro: 'Use these buttons to quickly access common actions like calculating levies, importing data, or generating reports.',
                position: 'bottom'
            },
            {
                element: '#sidebarMenu',
                title: 'Navigation',
                intro: 'Use this menu to navigate to different sections of the application.',
                position: 'right'
            }
        ]
    },
    
    // Levy Calculator tour
    levy_calculator: {
        steps: [
            {
                element: '#calculator-intro',
                title: 'Levy Calculator',
                intro: 'Welcome to the Levy Calculator! This tool helps you calculate property tax levies based on assessed values and tax rates.',
                position: 'bottom'
            },
            {
                element: '#district-selection',
                title: 'Select Tax District',
                intro: 'Start by selecting a tax district. This will load the associated tax codes and rates.',
                position: 'right'
            },
            {
                element: '#levy-parameters',
                title: 'Levy Parameters',
                intro: 'Enter your levy parameters here, including total assessed value and desired levy amount or rate.',
                position: 'bottom'
            },
            {
                element: '#calculator-results',
                title: 'Results',
                intro: 'The calculated results will appear here, showing the levy rate, total levy amount, and distribution across tax codes.',
                position: 'left'
            },
            {
                element: '#action-buttons',
                title: 'Actions',
                intro: 'Use these buttons to calculate, save, or export your levy calculations.',
                position: 'top'
            }
        ]
    },
    
    // Data Import tour
    data_import: {
        steps: [
            {
                element: '#import-intro',
                title: 'Data Import',
                intro: 'Welcome to the Data Import tool! This page helps you import tax district and property data into the system.',
                position: 'bottom'
            },
            {
                element: '#file-upload',
                title: 'Upload File',
                intro: 'Upload your data file here. The system supports various formats including TXT, XLS, XLSX, and XML.',
                position: 'right'
            },
            {
                element: '#import-options',
                title: 'Import Options',
                intro: 'Configure your import options here, including how to handle existing data and validation rules.',
                position: 'bottom'
            },
            {
                element: '#import-history',
                title: 'Import History',
                intro: 'View your previous imports, including status, date, and record counts.',
                position: 'left'
            }
        ]
    },
    
    // Property Search tour
    property_search: {
        steps: [
            {
                element: '#search-form',
                title: 'Property Search',
                intro: 'Welcome to Property Search! This tool helps you find properties by various criteria.',
                position: 'bottom'
            },
            {
                element: '#search-criteria',
                title: 'Search Criteria',
                intro: 'Enter your search criteria here. You can search by tax district, PIN, owner name, or address.',
                position: 'right'
            },
            {
                element: '#search-results',
                title: 'Search Results',
                intro: 'Your search results will appear here, showing property details and assessed values.',
                position: 'top'
            },
            {
                element: '#export-options',
                title: 'Export Options',
                intro: 'Use these options to export your search results to various formats.',
                position: 'left'
            }
        ]
    }
};

// Check if a tour should be started automatically
function checkForAutomaticTour() {
    // Get the current page from the URL path
    const path = window.location.pathname;
    
    // Get the tour parameter from the URL
    const urlParams = new URLSearchParams(window.location.search);
    const tourParam = urlParams.get('tour');
    
    // If there's a tour parameter, start that tour
    if (tourParam && tourConfigurations[tourParam]) {
        startTour(tourParam);
        return;
    }
    
    // Check if auto tours are enabled (default to true)
    const enableAutoTours = localStorage.getItem('enable_auto_tours') !== 'false';
    if (!enableAutoTours) {
        return;
    }
    
    // Determine which tour to show based on the current page
    let tourToShow = null;
    
    if (path.includes('/dashboard')) {
        tourToShow = 'dashboard';
    } else if (path.includes('/levy-calculator')) {
        tourToShow = 'levy_calculator';
    } else if (path.includes('/import')) {
        tourToShow = 'data_import';
    } else if (path.includes('/property-lookup')) {
        tourToShow = 'property_search';
    }
    
    // Check if the tour has already been completed
    if (tourToShow && !isTourCompleted(tourToShow)) {
        startTour(tourToShow);
    }
}

// Check if a tour has been completed
function isTourCompleted(tourName) {
    return localStorage.getItem(`tour_${tourName}_completed`) === 'true';
}

// Mark a tour as completed
function markTourCompleted(tourName) {
    localStorage.setItem(`tour_${tourName}_completed`, 'true');
}

// Start a specific tour
function startTour(tourName) {
    // Get the tour configuration
    const tourConfig = tourConfigurations[tourName];
    if (!tourConfig) {
        console.error(`Tour configuration not found for: ${tourName}`);
        return;
    }
    
    // Initialize IntroJS
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
        prevLabel: '← Back'
    });
    
    // Register event handlers
    intro.oncomplete(function() {
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
    startTour,
    checkForAutomaticTour,
    isTourCompleted,
    markTourCompleted
};
