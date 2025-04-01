"""
Tests for routes and API endpoints.
"""

import pytest
import json
import io
import os
from datetime import datetime
from werkzeug.datastructures import FileStorage
from models import Property, TaxCode, TaxDistrict, ImportLog, ExportLog


def test_index_route(client, seed_test_data):
    """Test the index route."""
    response = client.get('/')
    
    # Check status code
    assert response.status_code == 200
    
    # Check content
    assert b'Dashboard' in response.data
    assert b'Properties' in response.data
    assert b'Tax Codes' in response.data
    assert b'Districts' in response.data


def test_property_lookup_route(client, seed_test_data):
    """Test the property lookup route."""
    # Test GET request
    response = client.get('/property-lookup')
    assert response.status_code == 200
    assert b'Property Lookup' in response.data
    
    # Test POST request with valid property ID
    response = client.post('/property-lookup', data={
        'property_id': '12345-6789'
    })
    assert response.status_code == 200
    assert b'12345-6789' in response.data
    assert b'250000' in response.data  # Assessed value
    assert b'00120' in response.data   # Tax code
    
    # Test POST request with invalid property ID
    response = client.post('/property-lookup', data={
        'property_id': 'NONEXISTENT'
    })
    assert response.status_code == 200
    assert b'Property not found' in response.data


def test_districts_route(client, seed_test_data):
    """Test the districts route."""
    response = client.get('/districts')
    
    # Check status code
    assert response.status_code == 200
    
    # Check content
    assert b'Tax Districts' in response.data
    assert b'2023' in response.data  # Year
    assert b'00120' in response.data  # Levy code
    assert b'00130' in response.data  # Linked levy code


def test_levy_calculator_route(client, seed_test_data):
    """Test the levy calculator route."""
    # Test GET request
    response = client.get('/levy-calculator')
    assert response.status_code == 200
    assert b'Levy Calculator' in response.data
    assert b'00120' in response.data  # Tax code
    assert b'00130' in response.data  # Tax code
    
    # Test POST request with levy amounts
    response = client.post('/levy-calculator', data={
        'levy_amount_00120': '1200000',
        'levy_amount_00130': '600000'
    })
    assert response.status_code == 200
    assert b'Levy Rate: 3.00' in response.data or b'Levy Rate: 3,00' in response.data  # For 00120
    assert b'Levy Rate: 3.72' in response.data or b'Levy Rate: 3,72' in response.data  # For 00130


def test_reports_route(client, seed_test_data):
    """Test the reports route."""
    response = client.get('/reports')
    
    # Check status code
    assert response.status_code == 200
    
    # Check content
    assert b'Reports' in response.data
    assert b'Tax Roll Export' in response.data


def test_api_tax_codes(client, seed_test_data):
    """Test the API endpoint for tax codes."""
    response = client.get('/api/tax-codes')
    
    # Check status code
    assert response.status_code == 200
    
    # Parse JSON response
    data = json.loads(response.data)
    
    # Check structure
    assert 'tax_codes' in data
    assert len(data['tax_codes']) == 2
    
    # Check content
    tax_codes = data['tax_codes']
    assert any(tc['code'] == '00120' for tc in tax_codes)
    assert any(tc['code'] == '00130' for tc in tax_codes)
    
    # Check fields
    for tc in tax_codes:
        assert 'code' in tc
        assert 'levy_rate' in tc
        assert 'total_assessed_value' in tc
        assert 'property_count' in tc


def test_api_district_summary(client, seed_test_data):
    """Test the API endpoint for district summary."""
    response = client.get('/api/district-summary')
    
    # Check status code
    assert response.status_code == 200
    
    # Parse JSON response
    data = json.loads(response.data)
    
    # Check structure
    assert 'districts' in data
    assert 'year' in data
    
    # Check content
    districts = data['districts']
    assert len(districts) == 2
    
    # Check fields
    for district in districts:
        assert 'tax_district_id' in district
        assert 'year' in district
        assert 'levy_code' in district
        assert 'linked_levy_codes' in district