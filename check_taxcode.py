from app import create_app, db
from models import TaxCode

app = create_app()

with app.app_context():
    tax_code = TaxCode.query.first()
    if tax_code:
        print("Sample TaxCode attributes:")
        for attr in dir(tax_code):
            if not attr.startswith('_') and attr not in ('metadata', 'registry'):
                try:
                    value = getattr(tax_code, attr)
                    if not callable(value):
                        print(f"  - {attr}: {value}")
                except Exception as e:
                    print(f"  - {attr}: Error - {str(e)}")
    else:
        print("No TaxCode records found")
