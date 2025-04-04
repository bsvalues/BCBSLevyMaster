/**
 * Levy Calculation System - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
  console.log('Levy Calculation System JS initialized successfully');
  
  // Initialize components
  initializeGuidedTour();
  initializeHelpMenu();
  
  // Setup form validations
  setupFormValidations();
  
  // Initialize interactive elements
  initializeTooltips();
  initializeDataTables();
  
  // Handle flash messages auto-dismiss
  setupFlashMessages();
});

/**
 * Initialize the guided tour functionality
 */
function initializeGuidedTour() {
  console.log('Guided Tour System initialized');
  
  // Check if IntroJS is available
  if (typeof introJs !== 'undefined') {
    // Get all tour trigger elements
    const tourTriggers = document.querySelectorAll('[data-tour]');
    
    tourTriggers.forEach(trigger => {
      trigger.addEventListener('click', function() {
        const tourName = this.getAttribute('data-tour');
        startTour(tourName);
      });
    });
  }
}

/**
 * Start a guided tour based on the tour name
 * @param {string} tourName - The name of the tour to start
 */
function startTour(tourName) {
  try {
    // Define tour steps based on the tour name
    let steps = [];
    
    switch(tourName) {
      case 'dashboard':
        steps = [
          {
            element: document.querySelector('.dashboard-header'),
            intro: 'Welcome to the Levy Calculation System Dashboard!',
            position: 'bottom'
          },
          {
            element: document.querySelector('.dashboard-stats'),
            intro: 'Here you can see key statistics about your tax districts and properties.',
            position: 'bottom'
          },
          {
            element: document.querySelector('.nav'),
            intro: 'Use the navigation menu to access different features of the system.',
            position: 'bottom'
          }
        ];
        break;
        
      case 'levy-calculator':
        steps = [
          {
            element: document.querySelector('.calculator-form'),
            intro: 'This is the Levy Calculator. Enter your property information to calculate your tax levy.',
            position: 'right'
          },
          {
            element: document.querySelector('.tax-code-select'),
            intro: 'Select your tax code from this dropdown menu.',
            position: 'bottom'
          },
          {
            element: document.querySelector('.calculator-submit'),
            intro: 'Click this button to calculate your levy.',
            position: 'bottom'
          }
        ];
        break;
        
      case 'import':
        steps = [
          {
            element: document.querySelector('.import-form'),
            intro: 'Use this form to import your levy data.',
            position: 'right'
          },
          {
            element: document.querySelector('.file-upload'),
            intro: 'Select your file to upload. We support TXT, XLS, XLSX, and XML formats.',
            position: 'bottom'
          },
          {
            element: document.querySelector('.import-submit'),
            intro: 'Click this button to start the import process.',
            position: 'bottom'
          }
        ];
        break;
        
      default:
        console.log('Unknown tour name:', tourName);
        return;
    }
    
    // Start the tour
    const tour = introJs();
    tour.setOptions({
      steps: steps,
      showProgress: true,
      showBullets: false,
      showStepNumbers: false,
      overlayOpacity: 0.7,
      exitOnOverlayClick: true,
      nextLabel: 'Next',
      prevLabel: 'Back',
      doneLabel: 'Finish',
      tooltipClass: 'custom-tooltip',
      highlightClass: 'custom-highlight'
    });
    
    tour.start();
  } catch (e) {
    console.error('Error starting tour:', e);
  }
}

/**
 * Initialize the help menu functionality
 */
function initializeHelpMenu() {
  console.log('Initializing help menu...');
  
  // Create help menu button if it doesn't exist
  if (!document.querySelector('.help-menu-button')) {
    const helpButton = document.createElement('div');
    helpButton.className = 'help-menu-button';
    helpButton.innerHTML = '?';
    helpButton.setAttribute('title', 'Help Menu');
    document.body.appendChild(helpButton);
    
    // Create help menu container
    const helpMenu = document.createElement('div');
    helpMenu.className = 'help-menu';
    
    // Add help menu items
    helpMenu.innerHTML = `
      <div class="help-menu-item" data-tour="dashboard">Dashboard Tour</div>
      <div class="help-menu-item" data-tour="levy-calculator">Levy Calculator Tour</div>
      <div class="help-menu-item" data-tour="import">Import Data Tour</div>
      <div class="help-menu-item" data-action="glossary">Tax Glossary</div>
      <div class="help-menu-item" data-action="faq">FAQ</div>
      <div class="help-menu-item" data-action="support">Support</div>
    `;
    
    document.body.appendChild(helpMenu);
    
    // Add click event to help button
    helpButton.addEventListener('click', function() {
      helpMenu.classList.toggle('active');
    });
    
    // Add click events to help menu items
    const helpMenuItems = document.querySelectorAll('.help-menu-item');
    helpMenuItems.forEach(item => {
      item.addEventListener('click', function() {
        const tour = this.getAttribute('data-tour');
        const action = this.getAttribute('data-action');
        
        if (tour) {
          startTour(tour);
          helpMenu.classList.remove('active');
        }
        
        if (action) {
          handleHelpAction(action);
          helpMenu.classList.remove('active');
        }
      });
    });
    
    // Close help menu when clicking outside
    document.addEventListener('click', function(event) {
      if (!helpMenu.contains(event.target) && !helpButton.contains(event.target)) {
        helpMenu.classList.remove('active');
      }
    });
  }
  
  console.log('Help Menu System initialized');
}

/**
 * Handle help menu actions
 * @param {string} action - The action to perform
 */
function handleHelpAction(action) {
  switch(action) {
    case 'glossary':
      window.location.href = '/glossary';
      break;
    case 'faq':
      window.location.href = '/faq';
      break;
    case 'support':
      window.location.href = '/support';
      break;
    default:
      console.log('Unknown help action:', action);
  }
}

/**
 * Setup form validations
 */
function setupFormValidations() {
  // Get all forms with validation
  const forms = document.querySelectorAll('.needs-validation');
  
  // Loop over them and prevent submission
  Array.from(forms).forEach(form => {
    form.addEventListener('submit', event => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      
      form.classList.add('was-validated');
    }, false);
  });
}

/**
 * Initialize tooltips
 */
function initializeTooltips() {
  // Check if Bootstrap is available
  if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    Array.from(tooltipTriggerList).map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
  }
}

/**
 * Initialize data tables
 */
function initializeDataTables() {
  // Check if DataTables is available
  if (typeof $.fn.DataTable !== 'undefined') {
    $('.data-table').DataTable({
      responsive: true,
      pageLength: 10,
      language: {
        search: "_INPUT_",
        searchPlaceholder: "Search records"
      }
    });
  }
}

/**
 * Setup flash messages auto-dismiss
 */
function setupFlashMessages() {
  const flashMessages = document.querySelectorAll('.alert-dismissible');
  
  flashMessages.forEach(message => {
    // Auto-dismiss flash messages after 5 seconds
    setTimeout(() => {
      if (message && message.parentNode) {
        message.classList.add('fade-out');
        setTimeout(() => {
          message.remove();
        }, 500);
      }
    }, 5000);
  });
}