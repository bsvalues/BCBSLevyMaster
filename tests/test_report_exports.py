"""
Tests for the enhanced data export and reporting system.

This module contains tests to verify the functionality of:
- Creating and managing report templates
- Generating reports in different formats (Excel, PDF, CSV)
- Custom report configurations
- Handling large data exports
"""

import unittest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import the reporting module (to be created)
from utils import report_utils


class TestReportExports(unittest.TestCase):
    """Test suite for report generation and export functionality."""
    
    def setUp(self):
        """Set up test data that can be used across test methods."""
        # Create temp directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Sample property data for reports
        self.property_data = [
            {'property_id': 'PROP001', 'assessed_value': 250000, 'tax_code': '12345', 'levy_rate': 10.5},
            {'property_id': 'PROP002', 'assessed_value': 350000, 'tax_code': '12345', 'levy_rate': 10.5},
            {'property_id': 'PROP003', 'assessed_value': 420000, 'tax_code': '23456', 'levy_rate': 11.2},
        ]
        
        # Sample tax code data
        self.tax_code_data = [
            {'code': '12345', 'levy_amount': 1500000, 'levy_rate': 10.5, 'total_assessed_value': 142857142},
            {'code': '23456', 'levy_amount': 2000000, 'levy_rate': 11.2, 'total_assessed_value': 178571428},
        ]
        
        # Sample report template
        self.sample_template = {
            'name': 'Property Tax Summary',
            'type': 'property',
            'sections': [
                {
                    'title': 'Property Information',
                    'fields': ['property_id', 'assessed_value', 'tax_code']
                },
                {
                    'title': 'Tax Calculation',
                    'fields': ['levy_rate', 'calculated_tax']
                }
            ],
            'sorting': {'field': 'property_id', 'direction': 'asc'},
            'filters': []
        }
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove any test files
        for file in os.listdir(self.test_dir):
            os.remove(os.path.join(self.test_dir, file))
        os.rmdir(self.test_dir)
    
    def test_report_template_creation(self):
        """Test creation and validation of report templates."""
        # Create a new template
        template_id = report_utils.create_template(self.sample_template)
        self.assertIsNotNone(template_id)
        
        # Retrieve the template
        retrieved_template = report_utils.get_template(template_id)
        self.assertEqual(retrieved_template['name'], 'Property Tax Summary')
        self.assertEqual(len(retrieved_template['sections']), 2)
        
        # Test template validation
        validation_result = report_utils.validate_template(self.sample_template)
        self.assertTrue(validation_result['valid'])
        
        # Test invalid template
        invalid_template = self.sample_template.copy()
        invalid_template['sections'] = []  # Empty sections should be invalid
        validation_result = report_utils.validate_template(invalid_template)
        self.assertFalse(validation_result['valid'])
        self.assertIn('error', validation_result)
    
    def test_excel_export_format(self):
        """Test Excel format exports."""
        # Set up export path
        export_path = os.path.join(self.test_dir, 'property_report.xlsx')
        
        # Create Excel report with property data
        with patch('utils.report_utils.get_property_data', return_value=self.property_data):
            result = report_utils.generate_excel_report(
                template_id=None,  # Using provided template instead
                template=self.sample_template,
                output_path=export_path
            )
        
        # Verify export was successful
        self.assertTrue(result['success'])
        self.assertTrue(os.path.exists(export_path))
        self.assertGreater(os.path.getsize(export_path), 0)
        
        # Verify the exported file structure using openpyxl
        # Note: We're not actually loading the file here to avoid
        # dependencies, but in a real test we would verify sheet names,
        # data presence, etc.
    
    def test_pdf_export_format(self):
        """Test PDF format exports."""
        # Set up export path
        export_path = os.path.join(self.test_dir, 'property_report.pdf')
        
        # Create PDF report with property data
        with patch('utils.report_utils.get_property_data', return_value=self.property_data):
            result = report_utils.generate_pdf_report(
                template_id=None,  # Using provided template instead
                template=self.sample_template,
                output_path=export_path
            )
        
        # Verify export was successful
        self.assertTrue(result['success'])
        self.assertTrue(os.path.exists(export_path))
        self.assertGreater(os.path.getsize(export_path), 0)
    
    def test_csv_export_format(self):
        """Test CSV format exports."""
        # Set up export path
        export_path = os.path.join(self.test_dir, 'property_report.csv')
        
        # Create CSV report with property data
        with patch('utils.report_utils.get_property_data', return_value=self.property_data):
            result = report_utils.generate_csv_report(
                template_id=None,  # Using provided template instead
                template=self.sample_template,
                output_path=export_path
            )
        
        # Verify export was successful
        self.assertTrue(result['success'])
        self.assertTrue(os.path.exists(export_path))
        self.assertGreater(os.path.getsize(export_path), 0)
        
        # Verify CSV content
        with open(export_path, 'r') as f:
            content = f.read()
            # CSV should have headers
            self.assertIn('property_id', content)
            self.assertIn('assessed_value', content)
            # Check for data
            self.assertIn('PROP001', content)
    
    def test_json_export_format(self):
        """Test JSON format exports."""
        # Set up export path
        export_path = os.path.join(self.test_dir, 'property_report.json')
        
        # Create JSON report with property data
        with patch('utils.report_utils.get_property_data', return_value=self.property_data):
            result = report_utils.generate_json_report(
                template_id=None,  # Using provided template instead
                template=self.sample_template,
                output_path=export_path
            )
        
        # Verify export was successful
        self.assertTrue(result['success'])
        self.assertTrue(os.path.exists(export_path))
        self.assertGreater(os.path.getsize(export_path), 0)
        
        # Verify JSON content
        with open(export_path, 'r') as f:
            data = json.load(f)
            self.assertEqual(len(data), len(self.property_data))
            self.assertEqual(data[0]['property_id'], 'PROP001')
    
    def test_report_with_filters(self):
        """Test report generation with filters applied."""
        # Create template with filters
        template_with_filter = self.sample_template.copy()
        template_with_filter['filters'] = [
            {'field': 'tax_code', 'operator': '==', 'value': '12345'}
        ]
        
        # Set up export path
        export_path = os.path.join(self.test_dir, 'filtered_report.csv')
        
        # Create report with filtered data
        with patch('utils.report_utils.get_property_data', return_value=self.property_data):
            result = report_utils.generate_csv_report(
                template_id=None,
                template=template_with_filter,
                output_path=export_path
            )
        
        # Verify export was successful
        self.assertTrue(result['success'])
        
        # Verify only filtered data is present
        with open(export_path, 'r') as f:
            content = f.read()
            # Should include properties with tax_code 12345
            self.assertIn('PROP001', content)
            self.assertIn('PROP002', content)
            # Should NOT include property with different tax_code
            self.assertNotIn('PROP003', content)
    
    def test_report_with_calculations(self):
        """Test reports with calculated fields."""
        # Create template with calculated fields
        template_with_calc = self.sample_template.copy()
        template_with_calc['sections'][1]['fields'] = [
            'levy_rate', 
            {'name': 'calculated_tax', 'formula': 'assessed_value / 1000 * levy_rate'}
        ]
        
        # Set up export path
        export_path = os.path.join(self.test_dir, 'calculated_report.csv')
        
        # Create report with calculated fields
        with patch('utils.report_utils.get_property_data', return_value=self.property_data):
            result = report_utils.generate_csv_report(
                template_id=None,
                template=template_with_calc,
                output_path=export_path
            )
        
        # Verify export was successful
        self.assertTrue(result['success'])
        
        # We would verify the calculated values in the output
        # but we'll skip detailed content verification for this test
    
    def test_large_data_exports(self):
        """Test exports with large datasets."""
        # Generate large sample data (1000 properties)
        large_data = []
        for i in range(1000):
            large_data.append({
                'property_id': f'PROP{i:04d}',
                'assessed_value': 200000 + (i * 1000),
                'tax_code': '12345' if i % 2 == 0 else '23456',
                'levy_rate': 10.5 if i % 2 == 0 else 11.2
            })
        
        # Set up export path
        export_path = os.path.join(self.test_dir, 'large_report.xlsx')
        
        # Create Excel report with large data
        with patch('utils.report_utils.get_property_data', return_value=large_data):
            result = report_utils.generate_excel_report(
                template_id=None,
                template=self.sample_template,
                output_path=export_path
            )
        
        # Verify export was successful
        self.assertTrue(result['success'])
        self.assertTrue(os.path.exists(export_path))
        
        # Verify performance metrics
        self.assertIn('generation_time', result)
        self.assertLess(result['generation_time'], 10.0)  # Should complete in under 10 seconds
    
    def test_report_template_management(self):
        """Test template management functions (list, update, delete)."""
        # Create a template
        template_id = report_utils.create_template(self.sample_template)
        
        # List templates
        templates = report_utils.list_templates()
        self.assertGreaterEqual(len(templates), 1)
        found = False
        for template in templates:
            if template['id'] == template_id:
                found = True
                break
        self.assertTrue(found)
        
        # Update template
        updated_template = self.sample_template.copy()
        updated_template['name'] = 'Updated Property Tax Summary'
        result = report_utils.update_template(template_id, updated_template)
        self.assertTrue(result['success'])
        
        # Verify update
        retrieved = report_utils.get_template(template_id)
        self.assertEqual(retrieved['name'], 'Updated Property Tax Summary')
        
        # Delete template
        result = report_utils.delete_template(template_id)
        self.assertTrue(result['success'])
        
        # Verify deletion
        with self.assertRaises(Exception):
            report_utils.get_template(template_id)
    
    def test_scheduled_report_generation(self):
        """Test scheduling a report for generation."""
        # Schedule a report
        schedule_config = {
            'template_id': 'temp123',  # Mocked template ID
            'format': 'excel',
            'frequency': 'weekly',
            'day': 'monday',
            'time': '08:00',
            'recipients': ['test@example.com'],
            'subject': 'Weekly Property Report'
        }
        
        with patch('utils.report_utils.create_scheduled_report') as mock_schedule:
            mock_schedule.return_value = {'id': 'sched123', 'success': True}
            result = report_utils.schedule_report(schedule_config)
            
            # Verify result
            self.assertTrue(result['success'])
            self.assertEqual(result['id'], 'sched123')
            
            # Verify correct arguments passed
            mock_schedule.assert_called_once()
            called_args = mock_schedule.call_args[0][0]
            self.assertEqual(called_args['frequency'], 'weekly')
            self.assertEqual(called_args['day'], 'monday')


if __name__ == '__main__':
    unittest.main()