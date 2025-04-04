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
        if (data.success) {
          alert("API key configuration received. In a production environment, this would update your system configuration.");
          // Close modal and reload page
          const modal = bootstrap.Modal.getInstance(document.getElementById("apiKeyModal"));
          if (modal) modal.hide();
          window.location.reload();
        } else {
          alert("Error: " + data.message);
        }
      })
      .catch(error => {
        alert("Error: " + error.message);
      });
    });
  }
  
  // Function to check API key status
  function checkApiKeyStatus() {
    fetch("/mcp/check-api-key")
      .then(response => response.json())
      .then(data => {
        const statusBadge = document.getElementById("apiKeyStatusBadge");
        if (statusBadge) {
          if (data.status === "valid") {
            statusBadge.className = "badge bg-success";
            statusBadge.innerHTML = "API Key Configured";
          } else if (data.status === "invalid") {
            statusBadge.className = "badge bg-danger";
            statusBadge.innerHTML = "Invalid API Key";
          } else {
            statusBadge.className = "badge bg-warning text-dark";
            statusBadge.innerHTML = "API Key Required";
          }
        }
      })
      .catch(error => {
        console.error("Error checking API key status:", error);
      });
  }
  
  // Check API key status on page load
  checkApiKeyStatus();
});
