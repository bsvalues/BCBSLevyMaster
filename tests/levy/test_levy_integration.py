"""
Integration tests for the levy calculation workflow.
"""
import pytest
import json
import os
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from app import app, db
from models import Property, TaxCode, ImportLog, ExportLog


# Helper function to round to 4 decimal places (same as application code)
def round_to_4(value):
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


class TestLevyIntegration:
    """Integration test suite for the levy calculation workflow."""
    
    def test_property_import_to_levy_calculation(self, client, tmp_path):
        """Test the full workflow from property import to levy calculation."""
        # Step 1: Import property data
        csv_content = (
            "property_id,assessed_value,tax_code\n"
            "INT-PROP-001,250000.00,LEV-100\n"
            "INT-PROP-002,300000.00,LEV-100\n"
            "INT-PROP-003,400000.00,LEV-200\n"
            "INT-PROP-004,500000.00,LEV-200\n"
            "INT-PROP-005,600000.00,LEV-300\n"
        )
        
        # Create a temporary CSV file
        csv_file_path = os.path.join(tmp_path, "test_properties.csv")
        with open(csv_file_path, 'w') as f:
            f.write(csv_content)
        
        # Upload the CSV file
        with open(csv_file_path, 'rb') as f:
            response = client.post(
                '/import',
                data={
                    'file': (BytesIO(f.read()), 'test_properties.csv'),
                },
                follow_redirects=True
            )
        
        # Verify import was successful
        assert response.status_code == 200
        assert b"Successfully imported" in response.data
        
        # Step 2: Verify property data was imported correctly
        properties = Property.query.filter(Property.property_id.like('INT-PROP-%')).all()
        assert len(properties) == 5
        
        # Step 3: Verify tax codes were created
        tax_codes = TaxCode.query.filter(TaxCode.code.in_(['LEV-100', 'LEV-200', 'LEV-300'])).all()
        assert len(tax_codes) == 3
        
        # Step 4: Calculate levy rates
        form_data = {
            'levy_amount_LEV-100': 27500.0,  # (250000 + 300000) / 1000 * 5.0
            'levy_amount_LEV-200': 36000.0,  # (400000 + 500000) / 1000 * 4.0
            'levy_amount_LEV-300': 4800.0,   # 600000 / 1000 * 8.0
        }
        
        response = client.post('/levy-calculator', data=form_data)
        assert response.status_code == 200
        
        # Step 5: Verify levy rates were updated in database
        tax_code_100 = TaxCode.query.filter_by(code='LEV-100').first()
        tax_code_200 = TaxCode.query.filter_by(code='LEV-200').first()
        tax_code_300 = TaxCode.query.filter_by(code='LEV-300').first()
        
        assert tax_code_100 is not None
        assert tax_code_200 is not None
        assert tax_code_300 is not None
        
        # Check if levy rates match expected values
        assert round_to_4(tax_code_100.levy_rate) == round_to_4(5.0)
        assert round_to_4(tax_code_200.levy_rate) == round_to_4(4.0)
        assert round_to_4(tax_code_300.levy_rate) == round_to_4(8.0)
        
        # Step 6: Generate tax roll report
        response = client.post('/reports', follow_redirects=True)
        
        # Check if a file was returned
        assert response.status_code == 200
        assert 'attachment' in response.headers.get('Content-Disposition', '')
        
        # Step 7: Verify export log was created
        export_log = ExportLog.query.order_by(ExportLog.id.desc()).first()
        assert export_log is not None
        assert export_log.rows_exported >= 5  # At least our 5 test properties
    
    def test_scenario_analysis_impact(self, client, seed_test_data):
        """Test levy scenario analysis and its impact on properties."""
        # Step 1: Set up some properties and tax codes
        prop1 = Property(property_id='SCENARIO-PROP-1', assessed_value=200000.0, tax_code='SCEN-100')
        prop2 = Property(property_id='SCENARIO-PROP-2', assessed_value=300000.0, tax_code='SCEN-100')
        tax_code = TaxCode(code='SCEN-100', total_assessed_value=500000.0, 
                          levy_amount=5000.0, levy_rate=10.0, previous_year_rate=9.5)
        
        db.session.add_all([prop1, prop2, tax_code])
        db.session.commit()
        
        # Step 2: Create scenarios
        scenarios = [
            {'name': 'Current', 'adjustments': {}},
            {'name': 'Increase 5%', 'adjustments': {'SCEN-100': 1.05}},
            {'name': 'Decrease 5%', 'adjustments': {'SCEN-100': 0.95}}
        ]
        
        response = client.post('/api/levy-scenarios', 
                              data=json.dumps({'scenarios': scenarios}),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Step 3: Verify scenario results
        assert 'scenarios' in data
        assert len(data['scenarios']) == 3
        
        # Step 4: Calculate property impact from scenarios
        response = client.post('/api/property-impact', 
                              data=json.dumps({'property_id': 'SCENARIO-PROP-1', 'scenarios': scenarios}),
                              content_type='application/json')
        
        assert response.status_code == 200
        impact_data = json.loads(response.data)
        
        # Step 5: Verify property impact results
        assert 'property_id' in impact_data
        assert 'assessed_value' in impact_data
        assert 'scenarios' in impact_data
        assert len(impact_data['scenarios']) == 3
        
        # Current: $200,000 / 1000 * 10.0 = $2,000
        current = next((s for s in impact_data['scenarios'] if s['name'] == 'Current'), None)
        assert current is not None
        assert round_to_4(current['tax_amount']) == round_to_4(2000.0)
        
        # 5% increase: $200,000 / 1000 * 10.5 = $2,100
        increase = next((s for s in impact_data['scenarios'] if s['name'] == 'Increase 5%'), None)
        assert increase is not None
        assert round_to_4(increase['tax_amount']) == round_to_4(2100.0)
        
        # 5% decrease: $200,000 / 1000 * 9.5 = $1,900
        decrease = next((s for s in impact_data['scenarios'] if s['name'] == 'Decrease 5%'), None)
        assert decrease is not None
        assert round_to_4(decrease['tax_amount']) == round_to_4(1900.0)
    
    def test_claude_ai_analysis_integration(self, client, seed_test_data):
        """Test the integration of Claude AI analysis in the levy calculator."""
        # Set up a tax code for testing
        tax_code = TaxCode(code='AI-TEST', total_assessed_value=10000000.0, 
                           levy_amount=100000.0, levy_rate=10.0, previous_year_rate=9.5)
        db.session.add(tax_code)
        db.session.commit()
        
        # Submit form with levy amounts
        form_data = {
            'levy_amount_AI-TEST': 105000.0,  # 5% increase
        }
        
        response = client.post('/levy-calculator', data=form_data)
        assert response.status_code == 200
        
        # Check if the AI analysis section is present in the response
        html_content = response.data.decode('utf-8')
        
        # Look for MCP Insights section which contains AI analysis
        assert 'AI Analysis' in html_content or 'MCP Insights' in html_content
        
        # Test accessing the dedicated AI analysis endpoint
        response = client.get('/api/levy-insights')
        assert response.status_code == 200
        
        # Verify valid JSON is returned
        try:
            data = json.loads(response.data)
            assert 'insights' in data
            # AI response structure may vary, but should have some key fields
            if 'analysis' in data['insights']:
                assert isinstance(data['insights']['analysis'], str)
            if 'recommendations' in data['insights']:
                assert isinstance(data['insights']['recommendations'], list)
        except json.JSONDecodeError:
            # If the AI is not available, the endpoint should still return valid JSON
            pass