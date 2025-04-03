/**
 * LevyMaster Help Menu System
 * 
 * Provides an interactive help menu with multiple tabs including:
 * - Guided Tours
 * - Documentation
 * - FAQ
 * - Support
 */

class HelpMenuSystem {
    constructor() {
        this.initialized = false;
        this.isOpen = false;
        
        // Initialize when DOM is loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    /**
     * Initialize the help menu system
     */
    init() {
        if (this.initialized) return;
        
        // Create the help menu HTML structure
        this.createHelpMenuStructure();
        
        // Set up event listeners
        this.setupEventListeners();
        
        this.initialized = true;
        console.log('Help Menu System initialized');
    }
    
    /**
     * Create the help menu HTML structure and append it to the body
     */
    createHelpMenuStructure() {
        const helpMenuHTML = `
            <div class="help-menu-overlay" id="helpMenuOverlay"></div>
            <div class="help-menu" id="helpMenu">
                <div class="help-menu-header">
                    <h5 class="help-menu-title"><i class="bi bi-question-circle me-2"></i>Help & Support Center</h5>
                    <button class="help-menu-close" id="helpMenuClose"><i class="bi bi-x-lg"></i></button>
                </div>
                <div class="help-menu-content">
                    <div class="help-menu-tabs">
                        <button class="help-tab active" data-tab="tours"><i class="bi bi-info-circle"></i>Guided Tours</button>
                        <button class="help-tab" data-tab="docs"><i class="bi bi-book"></i>Documentation</button>
                        <button class="help-tab" data-tab="faq"><i class="bi bi-question-lg"></i>FAQ</button>
                        <button class="help-tab" data-tab="support"><i class="bi bi-headset"></i>Support</button>
                    </div>
                    
                    <!-- Guided Tours Tab -->
                    <div class="help-tab-content active" id="toursTab">
                        <div class="p-3">
                            <h5 class="mb-3">Interactive Guided Tours</h5>
                            <p>Take a guided tour to learn how to use the Levy Calculation System. Select a tour below to get started:</p>
                        </div>
                        <ul class="help-menu-items">
                            <li class="help-menu-item" id="dashboardTourItem">
                                <div class="help-menu-item-icon">
                                    <i class="bi bi-house"></i>
                                </div>
                                <div class="help-menu-item-info">
                                    <div class="help-menu-item-title">Dashboard Tour</div>
                                    <div class="help-menu-item-description">Learn about the main features and navigation of the system.</div>
                                </div>
                            </li>
                            <li class="help-menu-item" id="calculationTourItem">
                                <div class="help-menu-item-icon">
                                    <i class="bi bi-calculator"></i>
                                </div>
                                <div class="help-menu-item-info">
                                    <div class="help-menu-item-title">Levy Calculation Tour</div>
                                    <div class="help-menu-item-description">Understand how to calculate property tax levies with compliance checks.</div>
                                </div>
                            </li>
                            <li class="help-menu-item" id="analysisTourItem">
                                <div class="help-menu-item-icon">
                                    <i class="bi bi-graph-up"></i>
                                </div>
                                <div class="help-menu-item-info">
                                    <div class="help-menu-item-title">Data Analysis Tour</div>
                                    <div class="help-menu-item-description">Learn how to analyze historical data and generate forecasts.</div>
                                </div>
                            </li>
                            <li class="help-menu-item" id="reportsTourItem">
                                <div class="help-menu-item-icon">
                                    <i class="bi bi-file-earmark-text"></i>
                                </div>
                                <div class="help-menu-item-info">
                                    <div class="help-menu-item-title">Reports Tour</div>
                                    <div class="help-menu-item-description">Discover how to generate and customize reports.</div>
                                </div>
                            </li>
                        </ul>
                    </div>
                    
                    <!-- Documentation Tab -->
                    <div class="help-tab-content" id="docsTab">
                        <div class="p-3">
                            <h5 class="mb-3">Documentation & Guides</h5>
                            <p>Access comprehensive documentation and user guides for the Levy Calculation System:</p>
                        </div>
                        <ul class="help-menu-items">
                            <li class="help-menu-item">
                                <div class="help-menu-item-icon">
                                    <i class="bi bi-file-earmark-text"></i>
                                </div>
                                <div class="help-menu-item-info">
                                    <div class="help-menu-item-title">User Manual</div>
                                    <div class="help-menu-item-description">Complete documentation of all features and functions.</div>
                                </div>
                            </li>
                            <li class="help-menu-item">
                                <div class="help-menu-item-icon">
                                    <i class="bi bi-journal-code"></i>
                                </div>
                                <div class="help-menu-item-info">
                                    <div class="help-menu-item-title">Levy Calculation Guide</div>
                                    <div class="help-menu-item-description">Learn about property tax calculations and compliance requirements.</div>
                                </div>
                            </li>
                            <li class="help-menu-item">
                                <div class="help-menu-item-icon">
                                    <i class="bi bi-upload"></i>
                                </div>
                                <div class="help-menu-item-info">
                                    <div class="help-menu-item-title">Data Import/Export Guide</div>
                                    <div class="help-menu-item-description">Instructions for importing and exporting data.</div>
                                </div>
                            </li>
                            <li class="help-menu-item">
                                <div class="help-menu-item-icon">
                                    <i class="bi bi-gear"></i>
                                </div>
                                <div class="help-menu-item-info">
                                    <div class="help-menu-item-title">Administrator Guide</div>
                                    <div class="help-menu-item-description">System management and configuration instructions.</div>
                                </div>
                            </li>
                        </ul>
                    </div>
                    
                    <!-- FAQ Tab -->
                    <div class="help-tab-content" id="faqTab">
                        <div class="p-3">
                            <h5 class="mb-3">Frequently Asked Questions</h5>
                            <p>Find answers to common questions about the Levy Calculation System:</p>
                            
                            <div class="help-faq-item">
                                <div class="help-faq-question">What is the Levy Calculation System?</div>
                                <div class="help-faq-answer">The Levy Calculation System is a comprehensive property tax management application that helps calculate levy rates, check statutory compliance, analyze historical data, and generate reports for various stakeholders.</div>
                            </div>
                            
                            <div class="help-faq-item">
                                <div class="help-faq-question">How do I import property data?</div>
                                <div class="help-faq-answer">Navigate to the Data Management section, select Import Data, and follow the guided process to upload your property data file. The system supports various formats including CSV, Excel, and XML.</div>
                            </div>
                            
                            <div class="help-faq-item">
                                <div class="help-faq-question">What statutory compliance checks are performed?</div>
                                <div class="help-faq-answer">The system performs various compliance checks based on Washington state laws, including levy rate limits, levy amount limits, new construction calculations, and assessed value thresholds. Each check is documented with the relevant statutory reference.</div>
                            </div>
                            
                            <div class="help-faq-item">
                                <div class="help-faq-question">Can I generate forecasts for future years?</div>
                                <div class="help-faq-answer">Yes, the Data Analysis section includes forecasting capabilities. You can generate projections based on historical trends, apply different forecasting models, and incorporate various scenarios for future planning.</div>
                            </div>
                            
                            <div class="help-faq-item">
                                <div class="help-faq-question">How often is the data backed up?</div>
                                <div class="help-faq-answer">The system automatically creates daily backups of all data. Administrators can also trigger manual backups at any time through the System Administration section.</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Support Tab -->
                    <div class="help-tab-content" id="supportTab">
                        <div class="p-3">
                            <h5 class="mb-3">Support & Contact</h5>
                            <p>Need additional help? Contact our support team or submit a support request:</p>
                            
                            <div class="help-support-section">
                                <h6><i class="bi bi-envelope me-2"></i>Contact Support</h6>
                                <p>For technical assistance or questions about the system, contact our support team:</p>
                                <ul>
                                    <li>Email: <a href="mailto:support@bentoncounty.gov">support@bentoncounty.gov</a></li>
                                    <li>Phone: (555) 123-4567</li>
                                    <li>Hours: Monday-Friday, 8:00 AM - 5:00 PM PT</li>
                                </ul>
                            </div>
                            
                            <div class="help-contact-form">
                                <h6>Submit a Support Request</h6>
                                <form id="supportForm">
                                    <div class="mb-3">
                                        <label for="supportName" class="form-label">Name</label>
                                        <input type="text" class="form-control" id="supportName" placeholder="Your name">
                                    </div>
                                    <div class="mb-3">
                                        <label for="supportEmail" class="form-label">Email</label>
                                        <input type="email" class="form-control" id="supportEmail" placeholder="Your email">
                                    </div>
                                    <div class="mb-3">
                                        <label for="supportSubject" class="form-label">Subject</label>
                                        <input type="text" class="form-control" id="supportSubject" placeholder="Subject">
                                    </div>
                                    <div class="mb-3">
                                        <label for="supportMessage" class="form-label">Message</label>
                                        <textarea class="form-control" id="supportMessage" rows="4" placeholder="Describe your issue or question..."></textarea>
                                    </div>
                                    <button type="submit" class="btn btn-primary">Submit Request</button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="help-menu-footer">
                    Levy Calculation System Help Center &copy; {{ current_year|default(2025) }} Benton County Assessor's Office
                </div>
            </div>
        `;
        
        // Create a container for the help menu
        const helpMenuContainer = document.createElement('div');
        helpMenuContainer.innerHTML = helpMenuHTML;
        
        // Append to the body
        document.body.appendChild(helpMenuContainer);
    }
    
    /**
     * Set up event listeners for the help menu
     */
    setupEventListeners() {
        // Get elements
        const helpButton = document.getElementById('help-button');
        const helpMenu = document.getElementById('helpMenu');
        const helpMenuOverlay = document.getElementById('helpMenuOverlay');
        const helpMenuClose = document.getElementById('helpMenuClose');
        const helpTabs = document.querySelectorAll('.help-tab');
        
        // Tour items
        const dashboardTourItem = document.getElementById('dashboardTourItem');
        const calculationTourItem = document.getElementById('calculationTourItem');
        const analysisTourItem = document.getElementById('analysisTourItem');
        const reportsTourItem = document.getElementById('reportsTourItem');
        
        // Support form
        const supportForm = document.getElementById('supportForm');
        
        // Toggle help menu when help button is clicked
        if (helpButton) {
            helpButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleHelpMenu();
            });
        }
        
        // Close help menu when overlay or close button is clicked
        if (helpMenuOverlay) {
            helpMenuOverlay.addEventListener('click', () => this.closeHelpMenu());
        }
        
        if (helpMenuClose) {
            helpMenuClose.addEventListener('click', () => this.closeHelpMenu());
        }
        
        // Tab switching
        helpTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                // Remove active class from all tabs and content
                helpTabs.forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.help-tab-content').forEach(c => c.classList.remove('active'));
                
                // Add active class to clicked tab and corresponding content
                tab.classList.add('active');
                const tabId = tab.getAttribute('data-tab');
                document.getElementById(`${tabId}Tab`).classList.add('active');
            });
        });
        
        // Tour items
        if (dashboardTourItem) {
            dashboardTourItem.addEventListener('click', () => {
                this.closeHelpMenu();
                if (window.guidedTourSystem) {
                    window.guidedTourSystem.startTour('dashboard');
                }
            });
        }
        
        if (calculationTourItem) {
            calculationTourItem.addEventListener('click', () => {
                this.closeHelpMenu();
                // TODO: Start calculation tour when available
                if (window.guidedTourSystem) {
                    alert('Levy Calculation tour will be available soon.');
                }
            });
        }
        
        if (analysisTourItem) {
            analysisTourItem.addEventListener('click', () => {
                this.closeHelpMenu();
                // TODO: Start analysis tour when available
                if (window.guidedTourSystem) {
                    alert('Data Analysis tour will be available soon.');
                }
            });
        }
        
        if (reportsTourItem) {
            reportsTourItem.addEventListener('click', () => {
                this.closeHelpMenu();
                // TODO: Start reports tour when available
                if (window.guidedTourSystem) {
                    alert('Reports tour will be available soon.');
                }
            });
        }
        
        // Support form submission
        if (supportForm) {
            supportForm.addEventListener('submit', (e) => {
                e.preventDefault();
                // TODO: Implement form submission
                alert('Support request submitted. Our team will contact you soon.');
                supportForm.reset();
            });
        }
        
        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeHelpMenu();
            }
        });
    }
    
    /**
     * Toggle the help menu open/closed
     */
    toggleHelpMenu() {
        const helpMenu = document.getElementById('helpMenu');
        const helpMenuOverlay = document.getElementById('helpMenuOverlay');
        
        if (this.isOpen) {
            this.closeHelpMenu();
        } else {
            helpMenu.classList.add('show');
            helpMenuOverlay.classList.add('show');
            this.isOpen = true;
        }
    }
    
    /**
     * Close the help menu
     */
    closeHelpMenu() {
        const helpMenu = document.getElementById('helpMenu');
        const helpMenuOverlay = document.getElementById('helpMenuOverlay');
        
        helpMenu.classList.remove('show');
        helpMenuOverlay.classList.remove('show');
        this.isOpen = false;
    }
}

// Initialize the help menu system when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.helpMenuSystem = new HelpMenuSystem();
});