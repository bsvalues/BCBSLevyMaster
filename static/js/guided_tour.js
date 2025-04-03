/**
 * LevyMaster Guided Tour System
 * 
 * Provides an interactive guided tour experience using Intro.js
 * to help users learn the Levy Calculation System functionality.
 */

// Define the tours
const TOURS = {
  // Dashboard Tour
  dashboard: [
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
  ],
  
  // Admin Dashboard Tour
  adminDashboard: [
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
  ]
};

// Current tour being displayed
let currentTour = null;

/**
 * Start a guided tour by name
 * 
 * @param {string} tourName - The name of the tour to start
 */
function startTour(tourName) {
  if (!TOURS[tourName]) {
    console.error(`Tour "${tourName}" not found.`);
    return;
  }
  
  currentTour = tourName;
  
  try {
    // Initialize intro.js
    const intro = window.introJs ? window.introJs() : null;
    if (!intro) {
      throw new Error("Intro.js is not available");
    }
    
    // Configure Intro.js
    intro.setOptions({
      steps: TOURS[tourName],
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
    intro.oncomplete(function() {
      console.log(`Tour "${tourName}" completed.`);
      localStorage.setItem(`tour_${tourName}_completed`, 'true');
      currentTour = null;
    });
    
    intro.onexit(function() {
      console.log(`Tour "${tourName}" exited.`);
      currentTour = null;
    });
    
    // Start the tour
    intro.start();
  } catch (e) {
    console.error('Error starting tour:', e);
  }
}

/**
 * Check if a tour should be automatically started based on page attributes
 */
function checkAutoStartTour() {
  const autoTourElement = document.querySelector('[data-auto-tour]');
  if (autoTourElement) {
    const tourName = autoTourElement.getAttribute('data-auto-tour');
    // Only auto-start for new users or if explicitly requested
    const hasSeenTour = localStorage.getItem(`tour_${tourName}_completed`);
    const forceAutoStart = new URLSearchParams(window.location.search).get('tour') === tourName;
    
    if (forceAutoStart || !hasSeenTour) {
      // Add slight delay to ensure page is fully loaded
      setTimeout(() => startTour(tourName), 1000);
    }
  }
}

/**
 * Reset a tour's "seen" status
 * 
 * @param {string} tourName - The name of the tour to reset
 */
function resetTour(tourName) {
  localStorage.removeItem(`tour_${tourName}_completed`);
  console.log(`Tour "${tourName}" reset. It will auto-start on next page load.`);
}

/**
 * Reset all tours
 */
function resetAllTours() {
  Object.keys(TOURS).forEach(tourName => {
    localStorage.removeItem(`tour_${tourName}_completed`);
  });
  console.log('All tours reset.');
}

// Initialize the guided tour system when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  try {
    console.log('Guided Tour System initialized');
    
    // Set up global access to tour functions
    window.guidedTourSystem = {
      startTour: startTour,
      resetTour: resetTour,
      resetAllTours: resetAllTours
    };
    
    // Check for auto-start tour
    checkAutoStartTour();
    
    // Set up click handler for help button
    const helpButton = document.getElementById('help-button');
    if (helpButton) {
      helpButton.addEventListener('click', function(e) {
        e.preventDefault();
        if (window.helpMenuSystem && typeof window.helpMenuSystem.toggleHelpMenu === 'function') {
          window.helpMenuSystem.toggleHelpMenu();
        } else {
          startTour('dashboard');
        }
      });
    }
  } catch (error) {
    console.error('Error initializing guided tour system:', error);
  }
});