/**
 * Anthropic API Key Configuration Utilities
 */

document.addEventListener("DOMContentLoaded", function() {
  // Handle save API key button click
  const saveApiKeyBtn = document.getElementById("saveApiKey");
  
  if (saveApiKeyBtn) {
    saveApiKeyBtn.addEventListener("click", function() {
      const apiKey = document.getElementById("apiKey").value.trim();
      
      if (!apiKey) {
        alert("Please enter a valid API key");
        return;
      }
      
      // Basic validation
      if (!apiKey.startsWith('sk-ant-')) {
        alert("Invalid API key format. Anthropic API keys should start with 'sk-ant-'");
        return;
      }
      
      // Update button state during submission
      saveApiKeyBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Validating...';
      saveApiKeyBtn.disabled = true;
      
      // Send API key to server
      fetch("/mcp/configure-api-key", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ api_key: apiKey })
      })
      .then(response => response.json())
      .then(data => {
        // Reset button state
        saveApiKeyBtn.innerHTML = 'Save API Key';
        saveApiKeyBtn.disabled = false;
        
        if (data.success) {
          // Close modal and display success message
          const modal = bootstrap.Modal.getInstance(document.getElementById("apiKeyModal"));
          if (modal) modal.hide();
          
          // Show a success toast
          showNotification("API Key Configured", "Your Anthropic API key has been successfully configured.", "success");
          
          // Reload page to reflect changes
          setTimeout(() => {
            window.location.reload();
          }, 1500);
        } else {
          // Show error message
          let errorMessage = data.message || "An error occurred while configuring the API key.";
          
          // Add detailed guidance based on status
          if (data.status === "no_credits") {
            errorMessage += " Please add credits to your Anthropic account or use a different API key.";
            showNotification("Credit Balance Issue", errorMessage, "warning");
          } else {
            showNotification("Configuration Error", errorMessage, "danger");
          }
        }
      })
      .catch(error => {
        // Reset button state
        saveApiKeyBtn.innerHTML = 'Save API Key';
        saveApiKeyBtn.disabled = false;
        
        showNotification("Error", "Error: " + error.message, "danger");
      });
    });
  }
  
  // Function to check API key status
  function checkApiKeyStatus() {
    fetch("/mcp/check-api-key")
      .then(response => response.json())
      .then(data => {
        const statusBadge = document.getElementById("apiKeyStatusBadge");
        const apiKeyMessage = document.getElementById("apiKeyMessage");
        
        if (statusBadge) {
          if (data.status === "valid") {
            statusBadge.className = "badge bg-success";
            statusBadge.innerHTML = "API Key Configured";
          } else if (data.status === "invalid") {
            statusBadge.className = "badge bg-danger";
            statusBadge.innerHTML = "Invalid API Key";
          } else if (data.status === "no_credits") {
            statusBadge.className = "badge bg-danger";
            statusBadge.innerHTML = "No API Credits";
          } else {
            statusBadge.className = "badge bg-warning text-dark";
            statusBadge.innerHTML = "API Key Required";
          }
        }
        
        // Display additional details if available
        if (apiKeyMessage && data.details) {
          const details = data.details;
          
          if (details.action_required) {
            let messageHTML = `
              <div class="alert ${data.status === 'no_credits' ? 'alert-danger' : 'alert-warning'} mb-0">
                <div class="d-flex align-items-center">
                  <div class="flex-shrink-0">
                    <i class="bi ${data.status === 'no_credits' ? 'bi-credit-card' : 'bi-key'} fs-3 me-3"></i>
                  </div>
                  <div class="flex-grow-1">
                    <h5 class="alert-heading">${data.status === 'no_credits' ? 'Credit Balance Issue' : 'API Key Required'}</h5>
                    <p>${details.suggestion || data.message}</p>
            `;
            
            if (details.help_link) {
              messageHTML += `
                    <div class="mt-2">
                      <a href="${details.help_link}" class="btn btn-sm btn-outline-${data.status === 'no_credits' ? 'danger' : 'primary'} me-2" target="_blank">
                        <i class="bi ${data.status === 'no_credits' ? 'bi-credit-card' : 'bi-key'} me-1"></i>
                        ${data.status === 'no_credits' ? 'Manage Credits' : 'Get API Key'}
                      </a>
                      <button type="button" class="btn btn-sm btn-outline-dark" data-bs-toggle="modal" data-bs-target="#apiKeyModal">
                        <i class="bi bi-gear me-1"></i>Configure Key
                      </button>
                    </div>
              `;
            }
            
            messageHTML += `
                  </div>
                </div>
              </div>
            `;
            
            apiKeyMessage.innerHTML = messageHTML;
          } else {
            apiKeyMessage.innerHTML = `
              <div class="alert alert-success mb-0">
                <i class="bi bi-check-circle-fill me-2"></i>
                ${details.suggestion || data.message}
              </div>
            `;
          }
        }
      })
      .catch(error => {
        console.error("Error checking API key status:", error);
        
        // Show error message
        const apiKeyMessage = document.getElementById("apiKeyMessage");
        if (apiKeyMessage) {
          apiKeyMessage.innerHTML = `
            <div class="alert alert-danger mb-0">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>
              Error checking API key status: ${error.message}
            </div>
          `;
        }
      });
  }
  
  // Helper function to show notifications
  function showNotification(title, message, type) {
    // Create a Bootstrap toast notification
    const toastContainer = document.createElement("div");
    toastContainer.className = "position-fixed bottom-0 end-0 p-3";
    toastContainer.style.zIndex = "5";
    
    // Create toast content
    toastContainer.innerHTML = `
      <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="toast-header bg-${type} text-white">
          <strong class="me-auto">${title}</strong>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
          ${message}
        </div>
      </div>
    `;
    
    // Add to document and auto-remove after delay
    document.body.appendChild(toastContainer);
    setTimeout(() => {
      toastContainer.remove();
    }, 5000);
  }
  
  // Check API key status on page load
  checkApiKeyStatus();
});
