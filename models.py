from datetime import datetime
from app import db

class Property(db.Model):
    """
    Model representing a property in the database.
    """
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    assessed_value = db.Column(db.Float, nullable=False)
    tax_code = db.Column(db.String(20), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Property {self.property_id}>"

class TaxCode(db.Model):
    """
    Model representing a tax code area with levy information.
    """
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    levy_amount = db.Column(db.Float, nullable=True)
    levy_rate = db.Column(db.Float, nullable=True)
    previous_year_rate = db.Column(db.Float, nullable=True)
    total_assessed_value = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TaxCode {self.code}>"

class TaxDistrict(db.Model):
    """
    Model representing a tax district with levy code relationships.
    """
    id = db.Column(db.Integer, primary_key=True)
    tax_district_id = db.Column(db.Integer, nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    levy_code = db.Column(db.String(20), nullable=False, index=True)
    linked_levy_code = db.Column(db.String(20), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('tax_district_id', 'year', 'levy_code', 'linked_levy_code', name='uix_tax_district_relationship'),
    )
    
    def __repr__(self):
        return f"<TaxDistrict {self.tax_district_id}-{self.year}-{self.levy_code}>"

class ImportLog(db.Model):
    """
    Model to log import operations.
    """
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    rows_imported = db.Column(db.Integer, nullable=False)
    rows_skipped = db.Column(db.Integer, nullable=False)
    warnings = db.Column(db.Text, nullable=True)
    import_date = db.Column(db.DateTime, default=datetime.utcnow)
    import_type = db.Column(db.String(50), nullable=True)  # 'property', 'district', etc.
    
    def __repr__(self):
        return f"<ImportLog {self.filename}>"

class ExportLog(db.Model):
    """
    Model to log export operations.
    """
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    rows_exported = db.Column(db.Integer, nullable=False)
    export_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ExportLog {self.filename}>"
