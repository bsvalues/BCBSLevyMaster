/**
 * Help Menu System for Levy Calculation System
 * 
 * This file contains functionality for the help menu system, which provides
 * users with quick access to tours, guides, and support resources.
 */

document.addEventListener('DOMContentLoaded', function() {
  console.log('Initializing help menu...');
  initializeHelpMenu();
});

/**
 * Initialize the help menu functionality
 */
function initializeHelpMenu() {
  // Get help button
  const helpButton = document.getElementById('help-button');
  
  if (!helpButton) {
    console.log('Help menu button not found');
    return;
  }
  
  // Create help menu if it doesn't exist
  let helpMenu = document.querySelector('.help-menu');
  
  if (!helpMenu) {
    helpMenu = createHelpMenu();
    document.body.appendChild(helpMenu);
  }
  
  // Toggle help menu when clicking the help button
  helpButton.addEventListener('click', function(e) {
    e.preventDefault();
    helpMenu.classList.toggle('active');
  });
  
  // Close help menu when clicking outside
  document.addEventListener('click', function(event) {
    if (helpMenu.classList.contains('active') && 
        !helpMenu.contains(event.target) && 
        !helpButton.contains(event.target)) {
      helpMenu.classList.remove('active');
    }
  });
  
  console.log('Help Menu System initialized');
}

/**
 * Create the help menu element
 * @returns {HTMLElement} The help menu element
 */
function createHelpMenu() {
  const helpMenu = document.createElement('div');
  helpMenu.className = 'help-menu';
  
  // Create help menu content
  helpMenu.innerHTML = `
    <div class="help-menu-header">
      <h5>Help & Resources</h5>
    </div>
    <div class="help-menu-body">
      <ul class="help-menu-items">
        <li class="help-menu-item" data-tour="dashboard">
          <i class="bi bi-info-circle"></i>
          Dashboard Tour
        </li>
        <li class="help-menu-item" data-tour="levyCalculator">
          <i class="bi bi-calculator"></i>
          Levy Calculator Tour
        </li>
        <li class="help-menu-item" data-tour="importData">
          <i class="bi bi-upload"></i>
          Import Data Tour
        </li>
        <li class="help-menu-item" data-action="glossary">
          <i class="bi bi-book"></i>
          Tax Glossary
        </li>
        <li class="help-menu-item" data-action="documentation">
          <i class="bi bi-file-text"></i>
          User Guide
        </li>
        <li class="help-menu-item" data-action="faq">
          <i class="bi bi-question-circle"></i>
          FAQ
        </li>
        <li class="help-menu-item" data-action="support">
          <i class="bi bi-headset"></i>
          Contact Support
        </li>
      </ul>
    </div>
  `;
  
  // Add event listeners to menu items
  setTimeout(() => {
    const items = helpMenu.querySelectorAll('.help-menu-item');
    
    items.forEach(item => {
      item.addEventListener('click', handleHelpMenuItemClick);
    });
  }, 0);
  
  return helpMenu;
}

/**
 * Handle help menu item clicks
 * @param {Event} e - Click event
 */
function handleHelpMenuItemClick(e) {
  const tourName = this.getAttribute('data-tour');
  const action = this.getAttribute('data-action');
  
  // Close the menu
  const helpMenu = document.querySelector('.help-menu');
  if (helpMenu) {
    helpMenu.classList.remove('active');
  }
  
  // Handle tour actions
  if (tourName) {
    // Check if the startTour function exists (defined in guided_tour.js)
    if (typeof startTour === 'function') {
      startTour(tourName);
    } else {
      console.error('Tour system not loaded');
    }
  }
  
  // Handle other actions
  if (action) {
    handleHelpAction(action);
  }
}

/**
 * Handle various help actions
 * @param {string} action - The action to perform
 */
function handleHelpAction(action) {
  switch (action) {
    case 'glossary':
      window.location.href = '/glossary';
      break;
      
    case 'documentation':
      window.location.href = '/help';
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