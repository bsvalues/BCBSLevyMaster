/**
 * Budget Impact Simulator
 *
 * This module provides interactive budget impact visualization capabilities,
 * allowing users to simulate tax rate and assessed value changes and view
 * the resulting impact on district budgets.
 */

// Initialize charts
let levyAmountChart;
let levyRateChart;

// Cache for district data to avoid repeated API calls
const districtDataCache = {};

// Charts configuration
const chartConfig = {
  levy: {
    type: 'bar',
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              if (context.parsed.y !== null) {
                label += new Intl.NumberFormat('en-US', {
                  style: 'currency',
                  currency: 'USD',
                  maximumFractionDigits: 0
                }).format(context.parsed.y);
              }
              return label;
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            display: false
          }
        },
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                notation: 'compact',
                compactDisplay: 'short',
                maximumFractionDigits: 0
              }).format(value);
            }
          }
        }
      }
    }
  },
  rate: {
    type: 'bar',
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              if (context.parsed.y !== null) {
                label += context.parsed.y.toFixed(2);
              }
              return label;
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            display: false
          }
        },
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return value.toFixed(2);
            }
          }
        }
      }
    }
  }
};

// Formatter for currency values
const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0
});

// Formatter for percentage values
const percentFormatter = new Intl.NumberFormat('en-US', {
  style: 'percent',
  signDisplay: 'always',
  maximumFractionDigits: 2
});

// Initialize the simulator when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  initializeUI();
  setupEventListeners();
  setupSliders();
  initializeCharts();
});

// Initialize the user interface
function initializeUI() {
  // Set initial values for sliders
  document.getElementById('taxRateValue').textContent = '0%';
  document.getElementById('assessedValueValue').textContent = '0%';
  
  // Apply to all districts toggle
  const applyToAllDistricts = document.getElementById('applyToAllDistricts');
  const districtTypeApplyContainer = document.getElementById('districtTypeApplyContainer');
  
  applyToAllDistricts.addEventListener('change', function() {
    districtTypeApplyContainer.style.display = this.checked ? 'none' : 'block';
  });
  
  // District type filters
  const districtTypeFilters = document.querySelectorAll('.district-type-filter');
  districtTypeFilters.forEach(filter => {
    filter.addEventListener('change', function() {
      filterDistrictsByType();
    });
  });
}

// Set up event listeners
function setupEventListeners() {
  // Year selection change
  const yearSelect = document.getElementById('yearSelect');
  if (yearSelect) {
    yearSelect.addEventListener('change', function() {
      window.location.href = window.location.pathname + '?year=' + this.value;
    });
  }
  
  // Run simulation button
  const runSimulationBtn = document.getElementById('runSimulation');
  if (runSimulationBtn) {
    runSimulationBtn.addEventListener('click', function() {
      runBudgetSimulation();
    });
  }
}

// Set up sliders with event listeners
function setupSliders() {
  // Tax rate slider
  const taxRateSlider = document.getElementById('taxRateSlider');
  const taxRateValue = document.getElementById('taxRateValue');
  
  if (taxRateSlider && taxRateValue) {
    taxRateSlider.addEventListener('input', function() {
      taxRateValue.textContent = this.value + '%';
    });
  }
  
  // Assessed value slider
  const assessedValueSlider = document.getElementById('assessedValueSlider');
  const assessedValueValue = document.getElementById('assessedValueValue');
  
  if (assessedValueSlider && assessedValueValue) {
    assessedValueSlider.addEventListener('input', function() {
      assessedValueValue.textContent = this.value + '%';
    });
  }
}

// Initialize the charts with empty data
function initializeCharts() {
  // Initialize levy amount chart
  const levyAmountCtx = document.getElementById('levyAmountChart');
  if (levyAmountCtx) {
    levyAmountChart = new Chart(levyAmountCtx, {
      type: chartConfig.levy.type,
      data: {
        labels: [],
        datasets: [
          {
            label: 'Baseline',
            data: [],
            backgroundColor: 'rgba(54, 162, 235, 0.6)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
          },
          {
            label: 'Simulation',
            data: [],
            backgroundColor: 'rgba(255, 99, 132, 0.6)',
            borderColor: 'rgba(255, 99, 132, 1)',
            borderWidth: 1
          }
        ]
      },
      options: chartConfig.levy.options
    });
  }
  
  // Initialize levy rate chart
  const levyRateCtx = document.getElementById('levyRateChart');
  if (levyRateCtx) {
    levyRateChart = new Chart(levyRateCtx, {
      type: chartConfig.rate.type,
      data: {
        labels: [],
        datasets: [
          {
            label: 'Baseline',
            data: [],
            backgroundColor: 'rgba(54, 162, 235, 0.6)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
          },
          {
            label: 'Simulation',
            data: [],
            backgroundColor: 'rgba(255, 99, 132, 0.6)',
            borderColor: 'rgba(255, 99, 132, 1)',
            borderWidth: 1
          }
        ]
      },
      options: chartConfig.rate.options
    });
  }
}

// Filter districts by selected types
function filterDistrictsByType() {
  const selectedTypes = [];
  document.querySelectorAll('.district-type-filter:checked').forEach(checkbox => {
    selectedTypes.push(checkbox.value);
  });
  
  const districtItems = document.querySelectorAll('.district-item');
  
  if (selectedTypes.length === 0) {
    // Show all if no filters selected
    districtItems.forEach(item => {
      item.style.display = 'block';
    });
  } else {
    // Show only matching districts
    districtItems.forEach(item => {
      const districtType = item.getAttribute('data-district-type');
      if (selectedTypes.includes(districtType)) {
        item.style.display = 'block';
      } else {
        item.style.display = 'none';
      }
    });
  }
}

// Run budget simulation with the current parameters
function runBudgetSimulation() {
  // Get selected districts
  const selectedDistricts = [];
  document.querySelectorAll('.district-checkbox:checked').forEach(checkbox => {
    selectedDistricts.push(parseInt(checkbox.value));
  });
  
  if (selectedDistricts.length === 0) {
    alert('Please select at least one district for simulation.');
    return;
  }
  
  // Get simulation parameters
  const taxRateChange = parseFloat(document.getElementById('taxRateSlider').value);
  const assessedValueChange = parseFloat(document.getElementById('assessedValueSlider').value);
  const applyToAll = document.getElementById('applyToAllDistricts').checked;
  
  // Get district type filters if not applying to all
  let districtTypeFilters = [];
  if (!applyToAll) {
    document.querySelectorAll('.district-type-apply:checked').forEach(checkbox => {
      districtTypeFilters.push(checkbox.value);
    });
  }
  
  // Get year from select
  const year = parseInt(document.getElementById('yearSelect').value);
  
  // Prepare request payload
  const payload = {
    year: year,
    district_ids: selectedDistricts,
    scenario: {
      rate_change_percent: taxRateChange,
      assessed_value_change_percent: assessedValueChange,
      district_type_filters: districtTypeFilters
    }
  };
  
  // Show loading state
  showLoadingState();
  
  // Call the simulation API
  fetch('/budget-impact/api/simulation', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return response.json();
  })
  .then(data => {
    // Update the UI with simulation results
    updateSimulationResults(data);
    hideLoadingState();
  })
  .catch(error => {
    console.error('Error running simulation:', error);
    alert('Error running simulation. Please try again.');
    hideLoadingState();
  });
}

// Show loading state while simulation is running
function showLoadingState() {
  const simulationSummaryContainer = document.getElementById('simulationSummaryContainer');
  simulationSummaryContainer.innerHTML = `
    <div class="loader-container">
      <div class="loader"></div>
      <p class="text-muted mt-2">Running simulation...</p>
    </div>
  `;
  
  document.getElementById('runSimulation').disabled = true;
}

// Hide loading state when simulation completes
function hideLoadingState() {
  document.getElementById('runSimulation').disabled = false;
}

// Update UI with simulation results
function updateSimulationResults(data) {
  updateSimulationSummary(data);
  updateCharts(data);
  updateImpactMetrics(data);
  updateDistrictImpactTable(data);
}

// Update the simulation summary panel
function updateSimulationSummary(data) {
  const summaryContainer = document.getElementById('simulationSummaryContainer');
  
  // Calculate overall summary metrics
  let totalBaselineLevy = 0;
  let totalSimulatedLevy = 0;
  
  // Sum up all district baseline and simulated levies
  Object.values(data.impact).forEach(impact => {
    totalBaselineLevy += impact.levy_amount.baseline;
    totalSimulatedLevy += impact.levy_amount.simulation;
  });
  
  const totalLevyChange = totalSimulatedLevy - totalBaselineLevy;
  const totalLevyChangePercent = (totalBaselineLevy > 0) ? 
    (totalLevyChange / totalBaselineLevy) * 100 : 0;
  
  // Determine impact class based on change direction
  let impactClass = 'impact-neutral';
  if (totalLevyChangePercent > 0.1) {
    impactClass = 'impact-increase';
  } else if (totalLevyChangePercent < -0.1) {
    impactClass = 'impact-decrease';
  }
  
  // Create summary content
  let summaryContent = `
    <div class="impact-summary">
      <div class="summary-row">
        <div class="summary-label">Total Baseline Levy:</div>
        <div>${currencyFormatter.format(totalBaselineLevy)}</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Total Simulated Levy:</div>
        <div>${currencyFormatter.format(totalSimulatedLevy)}</div>
      </div>
      <div class="summary-row">
        <div class="summary-label">Total Change:</div>
        <div class="${impactClass}">
          ${currencyFormatter.format(totalLevyChange)} 
          (${percentFormatter.format(totalLevyChangePercent/100)})
        </div>
      </div>
    </div>
    <div class="mt-3">
      <small class="text-muted">
        Simulation based on ${Object.keys(data.impact).length} districts
      </small>
    </div>
  `;
  
  summaryContainer.innerHTML = summaryContent;
}

// Update charts with simulation data
function updateCharts(data) {
  // Prepare data for charts
  const districts = Object.values(data.impact);
  
  // Sort districts by levy amount for better visualization
  districts.sort((a, b) => b.levy_amount.baseline - a.levy_amount.baseline);
  
  // Get top 10 districts by levy amount for readable charts
  const topDistricts = districts.slice(0, 10);
  
  // Labels (district names)
  const labels = topDistricts.map(d => d.district_name);
  
  // Levy amount data
  const baselineLevyAmounts = topDistricts.map(d => d.levy_amount.baseline);
  const simulatedLevyAmounts = topDistricts.map(d => d.levy_amount.simulation);
  
  // Levy rate data
  const baselineLevyRates = topDistricts.map(d => d.levy_rate.baseline);
  const simulatedLevyRates = topDistricts.map(d => d.levy_rate.simulation);
  
  // Update levy amount chart
  if (levyAmountChart) {
    levyAmountChart.data.labels = labels;
    levyAmountChart.data.datasets[0].data = baselineLevyAmounts;
    levyAmountChart.data.datasets[1].data = simulatedLevyAmounts;
    levyAmountChart.update();
  }
  
  // Update levy rate chart
  if (levyRateChart) {
    levyRateChart.data.labels = labels;
    levyRateChart.data.datasets[0].data = baselineLevyRates;
    levyRateChart.data.datasets[1].data = simulatedLevyRates;
    levyRateChart.update();
  }
}

// Update impact metrics display
function updateImpactMetrics(data) {
  // Calculate aggregate metrics
  let totalBaselineLevy = 0;
  let totalSimulatedLevy = 0;
  let totalBaselineAssessedValue = 0;
  let totalAvgTaxPerProperty = 0;
  let totalAvgTaxPerPropertySimulated = 0;
  let districtCount = 0;
  let propertyCount = 0;
  
  // Sum up metrics from all districts
  Object.values(data.baseline).forEach(district => {
    totalBaselineLevy += district.total_levy_amount || 0;
    totalBaselineAssessedValue += district.total_assessed_value || 0;
    totalAvgTaxPerProperty += district.avg_tax_per_property || 0;
    propertyCount += district.property_count || 0;
    districtCount++;
  });
  
  Object.values(data.simulation).forEach(district => {
    totalSimulatedLevy += district.total_levy_amount || 0;
    totalAvgTaxPerPropertySimulated += district.avg_tax_per_property || 0;
  });
  
  // Calculate average metrics
  const avgBaselineLevyRate = totalBaselineAssessedValue > 0 ? 
    (totalBaselineLevy / totalBaselineAssessedValue) * 1000 : 0;
  
  const avgSimulatedLevyRate = totalBaselineAssessedValue > 0 ? 
    (totalSimulatedLevy / totalBaselineAssessedValue) * 1000 : 0;
  
  const avgTaxPerProperty = propertyCount > 0 ? 
    totalAvgTaxPerProperty / districtCount : 0;
  
  const avgTaxPerPropertySimulated = propertyCount > 0 ? 
    totalAvgTaxPerPropertySimulated / districtCount : 0;
  
  // Calculate changes
  const totalLevyChange = totalSimulatedLevy - totalBaselineLevy;
  const totalLevyChangePercent = totalBaselineLevy > 0 ? 
    (totalLevyChange / totalBaselineLevy) * 100 : 0;
  
  const avgTaxChange = avgTaxPerPropertySimulated - avgTaxPerProperty;
  const avgTaxChangePercent = avgTaxPerProperty > 0 ? 
    (avgTaxChange / avgTaxPerProperty) * 100 : 0;
  
  const avgRateChange = avgSimulatedLevyRate - avgBaselineLevyRate;
  const avgRateChangePercent = avgBaselineLevyRate > 0 ? 
    (avgRateChange / avgBaselineLevyRate) * 100 : 0;
  
  // Update metric display
  document.getElementById('baselineTotalLevy').textContent = currencyFormatter.format(totalBaselineLevy);
  document.getElementById('simulatedTotalLevy').textContent = currencyFormatter.format(totalSimulatedLevy);
  document.getElementById('simulatedTotalLevyChange').textContent = `${percentFormatter.format(totalLevyChangePercent/100)} change`;
  document.getElementById('simulatedTotalLevyChange').className = getImpactClass(totalLevyChangePercent);
  
  document.getElementById('avgTaxPerProperty').textContent = currencyFormatter.format(avgTaxPerPropertySimulated);
  document.getElementById('avgTaxPerPropertyChange').textContent = `${percentFormatter.format(avgTaxChangePercent/100)} change`;
  document.getElementById('avgTaxPerPropertyChange').className = getImpactClass(avgTaxChangePercent);
  
  document.getElementById('avgLevyRate').textContent = avgSimulatedLevyRate.toFixed(2);
  document.getElementById('avgLevyRateChange').textContent = `${percentFormatter.format(avgRateChangePercent/100)} change`;
  document.getElementById('avgLevyRateChange').className = getImpactClass(avgRateChangePercent);
}

// Update district impact table
function updateDistrictImpactTable(data) {
  const tableBody = document.getElementById('districtImpactTableBody');
  tableBody.innerHTML = '';
  
  // Convert impact object to array and sort by levy amount (descending)
  const districts = Object.values(data.impact).sort((a, b) => 
    b.levy_amount.baseline - a.levy_amount.baseline
  );
  
  // Create table rows for each district
  districts.forEach(district => {
    const row = document.createElement('tr');
    
    // District name
    const nameCell = document.createElement('td');
    nameCell.textContent = district.district_name;
    row.appendChild(nameCell);
    
    // District type
    const typeCell = document.createElement('td');
    typeCell.textContent = district.district_type;
    row.appendChild(typeCell);
    
    // Baseline levy
    const baselineCell = document.createElement('td');
    baselineCell.textContent = currencyFormatter.format(district.levy_amount.baseline);
    row.appendChild(baselineCell);
    
    // Simulated levy
    const simulatedCell = document.createElement('td');
    simulatedCell.textContent = currencyFormatter.format(district.levy_amount.simulation);
    row.appendChild(simulatedCell);
    
    // Change ($)
    const changeCell = document.createElement('td');
    changeCell.textContent = currencyFormatter.format(district.levy_amount.change);
    changeCell.className = getImpactClass(district.levy_amount.percent);
    row.appendChild(changeCell);
    
    // Change (%)
    const percentCell = document.createElement('td');
    percentCell.textContent = percentFormatter.format(district.levy_amount.percent/100);
    percentCell.className = getImpactClass(district.levy_amount.percent);
    row.appendChild(percentCell);
    
    tableBody.appendChild(row);
  });
}

// Helper function to get impact CSS class based on percent change
function getImpactClass(percentChange) {
  if (percentChange > 0.1) {
    return 'impact-increase';
  } else if (percentChange < -0.1) {
    return 'impact-decrease';
  } else {
    return 'impact-neutral';
  }
}
