/**
 * Historical data import/export preview functionality
 * 
 * This module provides functionality for:
 * - Previewing historical data before export
 * - Previewing CSV data before import
 * - Downloading a CSV template for import
 */

document.addEventListener('DOMContentLoaded', function() {
    // Export Preview Functionality
    const previewExportBtn = document.getElementById('previewExportBtn');
    if (previewExportBtn) {
        previewExportBtn.addEventListener('click', function() {
            // Get filter values
            const yearFilter = document.getElementById('export_year').value;
            const taxCodeFilter = document.getElementById('export_tax_code').value;
            
            // Build query string
            const queryParams = new URLSearchParams();
            if (yearFilter) queryParams.append('year', yearFilter);
            if (taxCodeFilter) queryParams.append('tax_code', taxCodeFilter);
            
            // Show the modal
            const exportPreviewModal = new bootstrap.Modal(document.getElementById('exportPreviewModal'));
            exportPreviewModal.show();
            
            // Show loading state
            document.getElementById('exportPreviewLoading').classList.remove('d-none');
            document.getElementById('exportPreviewContent').classList.add('d-none');
            document.getElementById('exportPreviewNoData').classList.add('d-none');
            
            // Fetch preview data
            fetch(`/api/historical_export_preview?${queryParams.toString()}`)
                .then(response => response.json())
                .then(data => {
                    // Hide loading state
                    document.getElementById('exportPreviewLoading').classList.add('d-none');
                    
                    if (data.success && data.preview && data.preview.length > 0) {
                        // Show preview content
                        document.getElementById('exportPreviewContent').classList.remove('d-none');
                        
                        // Populate the table
                        const tbody = document.querySelector('#exportPreviewTable tbody');
                        tbody.innerHTML = '';
                        
                        data.preview.forEach(row => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td>${row.tax_code}</td>
                                <td>${row.year}</td>
                                <td>${parseFloat(row.levy_rate).toFixed(4)}</td>
                                <td>${row.levy_amount ? parseFloat(row.levy_amount).toLocaleString() : 'N/A'}</td>
                                <td>${row.total_assessed_value ? parseFloat(row.total_assessed_value).toLocaleString() : 'N/A'}</td>
                            `;
                            tbody.appendChild(tr);
                        });
                        
                        // Set up confirm export button
                        document.getElementById('confirmExportBtn').onclick = function() {
                            const exportForm = document.querySelector('form[name="export_form"]');
                            exportForm.querySelector('input[name="export_historical_data"]').value = 'true';
                            exportForm.submit();
                        };
                    } else {
                        // Show no data message
                        document.getElementById('exportPreviewNoData').classList.remove('d-none');
                    }
                })
                .catch(error => {
                    console.error('Error fetching export preview:', error);
                    document.getElementById('exportPreviewLoading').classList.add('d-none');
                    document.getElementById('exportPreviewNoData').classList.remove('d-none');
                    document.getElementById('exportPreviewNoData').textContent = 'Error loading preview data. Please try again.';
                });
        });
    }
    
    // Import Preview Functionality
    const previewImportBtn = document.getElementById('previewImportBtn');
    if (previewImportBtn) {
        previewImportBtn.addEventListener('click', function() {
            const fileInput = document.getElementById('csv_file');
            
            if (fileInput.files.length === 0) {
                alert('Please select a CSV file first');
                return;
            }
            
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('csv_file', file);
            
            // Show the modal
            const importPreviewModal = new bootstrap.Modal(document.getElementById('importPreviewModal'));
            importPreviewModal.show();
            
            // Show loading state
            document.getElementById('importPreviewLoading').classList.remove('d-none');
            document.getElementById('importPreviewContent').classList.add('d-none');
            document.getElementById('importPreviewNoData').classList.add('d-none');
            document.getElementById('importValidationErrors').classList.add('d-none');
            
            // Fetch preview data
            fetch('/api/historical_import_preview', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Hide loading state
                document.getElementById('importPreviewLoading').classList.add('d-none');
                
                if (data.success) {
                    // Show preview content
                    document.getElementById('importPreviewContent').classList.remove('d-none');
                    
                    // Update statistics
                    document.getElementById('rowsToImport').textContent = data.stats.to_import;
                    document.getElementById('rowsToUpdate').textContent = data.stats.to_update;
                    document.getElementById('rowsToSkip').textContent = data.stats.to_skip;
                    document.getElementById('uniqueTaxCodes').textContent = data.stats.unique_tax_codes;
                    
                    // Show validation errors if any
                    if (data.warnings && data.warnings.length > 0) {
                        document.getElementById('importValidationErrors').classList.remove('d-none');
                        const errorList = document.getElementById('importValidationErrorsList');
                        errorList.innerHTML = '';
                        
                        data.warnings.forEach(warning => {
                            const li = document.createElement('li');
                            li.textContent = warning;
                            errorList.appendChild(li);
                        });
                    }
                    
                    // Populate the table
                    if (data.preview && data.preview.length > 0) {
                        const tbody = document.querySelector('#importPreviewTable tbody');
                        tbody.innerHTML = '';
                        
                        data.preview.forEach((row, index) => {
                            const tr = document.createElement('tr');
                            
                            // Determine row status
                            let statusBadge = '';
                            if (row.status === 'new') {
                                statusBadge = '<span class="badge bg-success">New</span>';
                            } else if (row.status === 'update') {
                                statusBadge = '<span class="badge bg-warning">Update</span>';
                            } else if (row.status === 'skip') {
                                statusBadge = '<span class="badge bg-danger">Skip</span>';
                                tr.classList.add('table-danger');
                            }
                            
                            tr.innerHTML = `
                                <td>${index + 1}</td>
                                <td>${row.tax_code || 'N/A'}</td>
                                <td>${row.year || 'N/A'}</td>
                                <td>${row.levy_rate ? parseFloat(row.levy_rate).toFixed(4) : 'N/A'}</td>
                                <td>${row.levy_amount ? parseFloat(row.levy_amount).toLocaleString() : 'N/A'}</td>
                                <td>${row.total_assessed_value ? parseFloat(row.total_assessed_value).toLocaleString() : 'N/A'}</td>
                                <td>${statusBadge}</td>
                            `;
                            tbody.appendChild(tr);
                        });
                        
                        // Set up confirm import button
                        document.getElementById('confirmImportBtn').onclick = function() {
                            document.getElementById('importForm').submit();
                        };
                    } else {
                        document.getElementById('importPreviewNoData').classList.remove('d-none');
                    }
                } else {
                    // Show error message
                    document.getElementById('importPreviewNoData').classList.remove('d-none');
                    document.getElementById('importPreviewNoData').textContent = data.message || 'Error analyzing CSV file';
                }
            })
            .catch(error => {
                console.error('Error fetching import preview:', error);
                document.getElementById('importPreviewLoading').classList.add('d-none');
                document.getElementById('importPreviewNoData').classList.remove('d-none');
                document.getElementById('importPreviewNoData').textContent = 'Error analyzing CSV file. Please try again.';
            });
        });
    }
    
    // Download Template Button
    const downloadTemplateBtn = document.getElementById('downloadTemplateBtn');
    if (downloadTemplateBtn) {
        downloadTemplateBtn.addEventListener('click', function() {
            // Create a CSV template string
            const headers = ['Tax Code', 'Year', 'Levy Rate', 'Levy Amount', 'Total Assessed Value'];
            const sampleData = [
                ['100001', '2023', '0.1254', '1500000', '12000000'],
                ['100002', '2023', '0.1542', '2500000', '16000000'],
                ['100001', '2022', '0.1185', '1350000', '11400000']
            ];
            
            let csvContent = headers.join(',') + '\n';
            sampleData.forEach(row => {
                csvContent += row.join(',') + '\n';
            });
            
            // Create blob and download
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'historical_rates_template.csv');
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }
});