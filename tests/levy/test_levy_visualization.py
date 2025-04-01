"""
Tests for the levy rate calculator visualization and UI functionality.
"""
import pytest
import json
from flask import url_for

from app import app, db
from models import Property, TaxCode, TaxDistrict


class TestLevyVisualization:
    """Test suite for levy calculator visualization functionality."""
    
    def test_levy_calculator_render(self, client, seed_test_data):
        """Test that the levy calculator page renders correctly with all components."""
        response = client.get('/levy-calculator')
        
        # Verify successful response
        assert response.status_code == 200
        
        # Check for key UI elements in the response HTML
        html_content = response.data.decode('utf-8')
        assert 'Levy Calculator' in html_content
        assert 'Current Levy Rates' in html_content
        assert 'Historical Comparison' in html_content
        assert 'Levy Scenario Analysis' in html_content
    
    def test_levy_calculation_form_submission(self, client, seed_test_data):
        """Test that submitting the levy calculation form works correctly."""
        # Create data to send in the form
        tax_codes = TaxCode.query.all()
        form_data = {}
        
        # Add levy amounts for each tax code
        for tc in tax_codes[:3]:  # Use first 3 tax codes for testing
            form_data[f'levy_amount_{tc.code}'] = 100000.0
        
        # Submit the form
        response = client.post('/levy-calculator', data=form_data)
        
        # Verify successful response
        assert response.status_code == 200
        
        # Check that the results section is displayed
        html_content = response.data.decode('utf-8')
        assert 'Calculation Results' in html_content
        assert 'Original Rates' in html_content
        assert 'Limited Rates' in html_content
    
    def test_levy_historical_chart_api(self, client, seed_test_data):
        """Test the API endpoint for historical levy rate comparison."""
        response = client.get('/api/levy-historical')
        
        # Verify successful response
        assert response.status_code == 200
        
        # Verify valid JSON is returned
        try:
            data = json.loads(response.data)
            assert 'tax_codes' in data
            assert 'current_rates' in data
            assert 'previous_rates' in data
            
            # Verify data structure for charts
            assert isinstance(data['tax_codes'], list)
            assert isinstance(data['current_rates'], list)
            assert isinstance(data['previous_rates'], list)
            assert len(data['tax_codes']) == len(data['current_rates'])
            assert len(data['tax_codes']) == len(data['previous_rates'])
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON")
    
    def test_levy_scenario_analysis_api(self, client, seed_test_data):
        """Test the API endpoint for levy scenario analysis."""
        # Create request data with scenarios
        scenarios = [
            {'name': 'Current', 'adjustments': {}},
            {'name': '5% Increase', 'adjustments': {'adjustment_factor': 1.05}},
            {'name': '10% Decrease', 'adjustments': {'adjustment_factor': 0.9}}
        ]
        
        response = client.post('/api/levy-scenarios', 
                              data=json.dumps({'scenarios': scenarios}),
                              content_type='application/json')
        
        # Verify successful response
        assert response.status_code == 200
        
        # Verify valid JSON is returned
        try:
            data = json.loads(response.data)
            assert 'scenarios' in data
            assert len(data['scenarios']) == 3
            
            # Check each scenario has expected fields
            for scenario in data['scenarios']:
                assert 'name' in scenario
                assert 'rates' in scenario
                assert 'limited_rates' in scenario
                assert 'impact' in scenario
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON")
    
    def test_levy_distribution_visualization(self, client, seed_test_data):
        """Test the tax distribution visualization component."""
        response = client.get('/api/levy-distribution')
        
        # Verify successful response
        assert response.status_code == 200
        
        # Verify valid JSON is returned
        try:
            data = json.loads(response.data)
            assert 'districts' in data
            assert 'amounts' in data
            
            # Verify data structure for charts
            assert isinstance(data['districts'], list)
            assert isinstance(data['amounts'], list)
            assert len(data['districts']) == len(data['amounts'])
        except json.JSONDecodeError:
            pytest.fail("Response is not valid JSON")
            
    def test_statutory_limit_visualization(self, client, seed_test_data):
        """Test the statutory limit visualization component."""
        # Create data to send in the form
        tax_codes = TaxCode.query.all()
        form_data = {}
        
        # Add high levy amounts that would exceed statutory limits
        for tc in tax_codes[:3]:  # Use first 3 tax codes for testing
            form_data[f'levy_amount_{tc.code}'] = 500000.0  # High amount to trigger limits
        
        # Submit the form
        response = client.post('/levy-calculator', data=form_data)
        
        # Verify successful response
        assert response.status_code == 200
        
        # Check that the statutory limit warnings are displayed
        html_content = response.data.decode('utf-8')
        assert 'Statutory Limits Applied' in html_content
        assert 'Some rates were adjusted to comply with statutory limits' in html_content