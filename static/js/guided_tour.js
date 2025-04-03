/**
 * LevyMaster Guided Tour System
 * 
 * Provides an interactive guided tour experience using Intro.js
 * to help users learn the Levy Calculation System functionality.
 */

class GuidedTourSystem {
    constructor() {
        this.introJs = null;
        this.tours = {}; // Store tour definitions
        this.currentTour = null;
        
        // Initialize when DOM is loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    /**
     * Initialize the guided tour system
     */
    init() {
        // Check if Intro.js is loaded
        if (typeof window.introJs === 'undefined') {
            console.error('Intro.js is required for the guided tour system.');
            return;
        }
        
        this.introJs = window.introJs();
        
        // Define tours
        this.defineTours();
        
        // Check for auto-start tour
        this.checkAutoStartTour();
        
        console.log('Guided Tour System initialized');
    }
    
    /**
     * Define all available tours
     */
    defineTours() {
        // Dashboard Tour
        this.tours.dashboard = [
            {
                element: '#main-header',
                title: 'Welcome to the Levy Calculation System',
                intro: 'This guided tour will help you understand the main features of the system. Let\'s get started!',
                position: 'bottom'
            },
            {
                element: '[data-tour="public-lookup"]',
                title: 'Public Property Lookup',
                intro: 'Access the public-facing property lookup portal where residents can search for property tax information and explore tax districts.',
                position: 'bottom'
            },
            {
                element: '[data-tour="admin-dashboard"]',
                title: 'Admin Dashboard',
                intro: 'Access the administrative dashboard to manage the system, view reports, and perform administrative tasks.',
                position: 'bottom'
            },
            {
                element: '[data-tour="levy-calculation"]',
                title: 'Levy Calculation',
                intro: 'Calculate property tax levies with comprehensive statutory compliance checks to ensure accuracy and legal compliance.',
                position: 'right'
            },
            {
                element: '[data-tour="data-analysis"]',
                title: 'Data Analysis',
                intro: 'Analyze historical levy data and generate forecasts to support planning and decision-making.',
                position: 'top'
            },
            {
                element: '[data-tour="reports"]',
                title: 'Reports',
                intro: 'Generate comprehensive reports for various stakeholders, including property owners, administrators, and government officials.',
                position: 'left'
            },
            {
                element: '#system-status',
                title: 'System Status',
                intro: 'View the current status of the system and any important announcements.',
                position: 'top'
            },
            {
                element: '#help-button',
                title: 'Help & Support',
                intro: 'Access the help center for documentation, FAQs, and support resources.',
                position: 'left'
            }
        ];
        
        // Admin Dashboard Tour
        this.tours.adminDashboard = [
            {
                element: '#admin-header',
                title: 'Admin Dashboard',
                intro: 'Welcome to the administrative dashboard. This is where you can manage the system and access key administrative functions.',
                position: 'bottom'
            },
            {
                element: '#admin-quick-actions',
                title: 'Quick Actions',
                intro: 'Access frequently used administrative functions from this quick action panel.',
                position: 'right'
            },
            {
                element: '#admin-stats',
                title: 'System Statistics',
                intro: 'View key system statistics and metrics at a glance.',
                position: 'top'
            },
            {
                element: '#admin-recent-activity',
                title: 'Recent Activity',
                intro: 'Monitor recent system activity and user actions.',
                position: 'left'
            },
            {
                element: '#admin-nav',
                title: 'Navigation',
                intro: 'Access different sections of the administrative interface from this navigation menu.',
                position: 'right'
            }
        ];
        
        // TODO: Define additional tours as needed
    }
    
    /**
     * Check if a tour should be automatically started based on page attributes
     */
    checkAutoStartTour() {
        const autoTourElement = document.querySelector('[data-auto-tour]');
        if (autoTourElement) {
            const tourName = autoTourElement.getAttribute('data-auto-tour');
            // Only auto-start for new users or if explicitly requested
            const hasSeenTour = localStorage.getItem(`tour_${tourName}_completed`);
            const forceAutoStart = new URLSearchParams(window.location.search).get('tour') === tourName;
            
            if (forceAutoStart || !hasSeenTour) {
                // Add slight delay to ensure page is fully loaded
                setTimeout(() => this.startTour(tourName), 1000);
            }
        }
    }
    
    /**
     * Start a guided tour by name
     * 
     * @param {string} tourName - The name of the tour to start
     */
    startTour(tourName) {
        if (!this.tours[tourName]) {
            console.error(`Tour "${tourName}" not found.`);
            return;
        }
        
        this.currentTour = tourName;
        
        // Configure Intro.js
        this.introJs.setOptions({
            steps: this.tours[tourName],
            showBullets: true,
            showProgress: true,
            hideNext: false,
            hidePrev: false,
            nextLabel: 'Next',
            prevLabel: 'Previous',
            skipLabel: 'Skip',
            doneLabel: 'Finish'
        });
        
        // Add event listeners
        this.introJs.oncomplete(() => {
            this.onTourComplete(tourName);
        });
        
        this.introJs.onexit(() => {
            this.onTourExit(tourName);
        });
        
        // Start the tour
        this.introJs.start();
    }
    
    /**
     * Handle tour completion
     * 
     * @param {string} tourName - The name of the completed tour
     */
    onTourComplete(tourName) {
        console.log(`Tour "${tourName}" completed.`);
        localStorage.setItem(`tour_${tourName}_completed`, 'true');
        this.currentTour = null;
        
        // Record analytics (if available)
        if (typeof gtag !== 'undefined') {
            gtag('event', 'tour_complete', {
                'tour_name': tourName
            });
        }
    }
    
    /**
     * Handle tour exit (skipped)
     * 
     * @param {string} tourName - The name of the exited tour
     */
    onTourExit(tourName) {
        console.log(`Tour "${tourName}" exited.`);
        this.currentTour = null;
        
        // Record analytics (if available)
        if (typeof gtag !== 'undefined') {
            gtag('event', 'tour_exit', {
                'tour_name': tourName
            });
        }
    }
    
    /**
     * Reset a tour's "seen" status
     * 
     * @param {string} tourName - The name of the tour to reset
     */
    resetTour(tourName) {
        localStorage.removeItem(`tour_${tourName}_completed`);
        console.log(`Tour "${tourName}" reset. It will auto-start on next page load.`);
    }
    
    /**
     * Reset all tours
     */
    resetAllTours() {
        Object.keys(this.tours).forEach(tourName => {
            localStorage.removeItem(`tour_${tourName}_completed`);
        });
        console.log('All tours reset.');
    }
}

// Initialize the guided tour system when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.guidedTourSystem = new GuidedTourSystem();
});