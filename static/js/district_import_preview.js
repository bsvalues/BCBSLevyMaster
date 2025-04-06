/**
 * District Import Preview functionality
 * 
 * This script handles the animated preview functionality for district data imports,
 * showing the data that will be imported before committing it to the database.
 */

document.addEventListener('DOMContentLoaded', function() {
    const previewForm = document.getElementById('district-preview-form');
    const importForm = document.getElementById('district-import-form');
    const previewContainer = document.getElementById('preview-container');
    const previewResults = document.getElementById('preview-results');
    const previewLoader = document.getElementById('preview-loader');
    const previewError = document.getElementById('preview-error');
    const confirmImportBtn = document.getElementById('confirm-import');
    const cancelPreviewBtn = document.getElementById('cancel-preview');
    
    // Skip if we're not on the district import page
    if (!previewForm) return;
    
    previewForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Show loader and hide previous results
        previewLoader.classList.remove('d-none');
        previewError.classList.add('d-none');
        previewResults.classList.add('d-none');
        previewContainer.classList.remove('d-none');
        
        // Get form data
        const formData = new FormData(previewForm);
        
        // Send AJAX request to preview endpoint
        fetch('/data/api/preview-district-import', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Hide loader
            previewLoader.classList.add('d-none');
            
            if (data.success) {
                // Show success results
                previewResults.classList.remove('d-none');
                
                // Populate preview table
                const previewTable = document.getElementById('preview-table');
                const tbody = previewTable.querySelector('tbody');
                tbody.innerHTML = '';
                
                // Create header based on first district's fields
                const thead = previewTable.querySelector('thead');
                const headerRow = thead.querySelector('tr');
                headerRow.innerHTML = '';
                
                if (data.districts && data.districts.length > 0) {
                    // Extract columns from the first district
                    const columns = Object.keys(data.districts[0]);
                    
                    // Create header row
                    columns.forEach(column => {
                        const th = document.createElement('th');
                        th.textContent = column.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()); // Capitalize words
                        headerRow.appendChild(th);
                    });
                    
                    // Add rows with animation delay
                    data.districts.forEach((district, index) => {
                        const row = document.createElement('tr');
                        row.style.opacity = 0;
                        row.style.transform = 'translateY(20px)';
                        row.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                        row.style.transitionDelay = `${index * 0.1}s`;
                        
                        columns.forEach(column => {
                            const td = document.createElement('td');
                            
                            // Format the value based on column type
                            if (column === 'levy_rate' && district[column] !== null) {
                                td.textContent = district[column] ? `${district[column].toFixed(4)}%` : '';
                            } else if (column === 'levy_amount' && district[column] !== null) {
                                td.textContent = district[column] ? `$${district[column].toLocaleString()}` : '';
                            } else {
                                td.textContent = district[column] !== null ? district[column] : '';
                            }
                            
                            row.appendChild(td);
                        });
                        
                        tbody.appendChild(row);
                        
                        // Trigger animation after a short delay
                        setTimeout(() => {
                            row.style.opacity = 1;
                            row.style.transform = 'translateY(0)';
                        }, 50);
                    });
                    
                    // Update summary
                    document.getElementById('preview-count').textContent = data.total_count;
                    document.getElementById('preview-sample-count').textContent = data.sample_count;
                    
                    // Show confirmation buttons
                    confirmImportBtn.classList.remove('d-none');
                    cancelPreviewBtn.classList.remove('d-none');
                    
                    // Prepare import form data
                    const fileInput = previewForm.querySelector('input[type="file"]');
                    const yearInput = previewForm.querySelector('select[name="year"]');
                    
                    // Update hidden fields in the import form
                    const importFileInput = document.getElementById('import-file-data');
                    const importYearInput = document.getElementById('import-year');
                    
                    // We can't transfer the file directly, so we'll submit both forms
                    importYearInput.value = yearInput.value;
                    
                    // Set up confirm button to trigger the actual import
                    confirmImportBtn.addEventListener('click', function() {
                        // Clone the file input to the import form
                        const originalFile = fileInput.files[0];
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(originalFile);
                        
                        const importFormFileInput = document.getElementById('import-file');
                        importFormFileInput.files = dataTransfer.files;
                        
                        // Submit the import form
                        importForm.submit();
                    });
                } else {
                    // No districts found
                    previewError.textContent = 'No valid district data found in the file';
                    previewError.classList.remove('d-none');
                    previewResults.classList.add('d-none');
                }
            } else {
                // Show error
                previewError.textContent = data.message || 'Failed to preview district data';
                previewError.classList.remove('d-none');
                previewResults.classList.add('d-none');
            }
        })
        .catch(error => {
            // Hide loader and show error
            previewLoader.classList.add('d-none');
            previewError.textContent = error.message || 'An unexpected error occurred';
            previewError.classList.remove('d-none');
            previewResults.classList.add('d-none');
        });
    });
    
    // Cancel preview button event
    if (cancelPreviewBtn) {
        cancelPreviewBtn.addEventListener('click', function() {
            previewContainer.classList.add('d-none');
        });
    }
});
