import csv
from app import db
from models import Property, TaxCode, ExportLog

def generate_tax_roll(file_path):
    """
    Generate a tax roll CSV file with property tax calculations.
    
    Args:
        file_path: Path to save the CSV file
        
    Returns:
        Number of rows exported
    """
    # Get all properties and join with tax codes to get levy rates
    query = db.session.query(
        Property.property_id,
        Property.assessed_value,
        Property.tax_code,
        TaxCode.levy_rate
    ).join(
        TaxCode,
        Property.tax_code == TaxCode.code
    ).filter(
        TaxCode.levy_rate.isnot(None)
    ).order_by(
        Property.tax_code,
        Property.property_id
    )
    
    properties = query.all()
    
    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(['Property ID', 'Assessed Value', 'Tax Code', 'Levy Rate', 'Calculated Tax'])
        
        # Write property data
        row_count = 0
        for prop in properties:
            property_id, assessed_value, tax_code, levy_rate = prop
            
            # Calculate tax
            calculated_tax = (assessed_value / 1000) * levy_rate
            
            writer.writerow([
                property_id,
                f"{assessed_value:.2f}",
                tax_code,
                f"{levy_rate:.4f}",
                f"{calculated_tax:.2f}"
            ])
            
            row_count += 1
    
    return row_count
