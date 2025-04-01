"""
Database models for the Levy Calculation System.
"""

import inspect
from datetime import datetime
from sqlalchemy.inspection import inspect
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, UniqueConstraint, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from app2 import db

class Property(db.Model):
    """Model for storing property assessment data."""
    __tablename__ = 'property'
    
    id = Column(Integer, primary_key=True)
    property_id = Column(String(50), unique=True, nullable=False, index=True)
    address = Column(String(255), nullable=True)
    owner_name = Column(String(255), nullable=True)
    assessed_value = Column(Float, nullable=False)
    tax_code = Column(String(20), ForeignKey('tax_code.code'), nullable=False, index=True)
    property_type = Column(String(50), nullable=True)
    year = Column(Integer, nullable=False, default=lambda: datetime.now().year)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tax_code_rel = relationship('TaxCode', back_populates='properties')
    
    def __repr__(self):
        return f"<Property(id={self.id}, property_id='{self.property_id}', value={self.assessed_value})>"

class TaxCode(db.Model):
    """Model for storing tax codes and their associated rates."""
    __tablename__ = 'tax_code'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    total_assessed_value = Column(Float, nullable=True)
    levy_rate = Column(Float, nullable=True)  # Per $1,000 of assessed value
    levy_amount = Column(Float, nullable=True)  # Total levy amount for this code
    year = Column(Integer, nullable=False, default=lambda: datetime.now().year)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    properties = relationship('Property', back_populates='tax_code_rel')
    districts = relationship('TaxDistrict', back_populates='tax_code_rel')
    historical_rates = relationship('TaxCodeHistoricalRate', back_populates='tax_code')
    
    def __repr__(self):
        return f"<TaxCode(id={self.id}, code='{self.code}', rate={self.levy_rate})>"

class TaxDistrict(db.Model):
    """Model for storing tax district information."""
    __tablename__ = 'tax_district'
    
    id = Column(Integer, primary_key=True)
    tax_district_id = Column(String(20), nullable=False, index=True)
    district_name = Column(String(255), nullable=False)
    levy_code = Column(String(20), ForeignKey('tax_code.code'), nullable=False, index=True)
    year = Column(Integer, nullable=False, default=lambda: datetime.now().year)
    statutory_limit = Column(Float, nullable=True)  # Maximum statutory levy rate
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tax_code_rel = relationship('TaxCode', back_populates='districts')
    
    # Unique constraint for district_id and year
    __table_args__ = (
        UniqueConstraint('tax_district_id', 'year', name='uix_district_year'),
    )
    
    def __repr__(self):
        return f"<TaxDistrict(id={self.id}, district_id='{self.tax_district_id}', name='{self.district_name}')>"

class ImportLog(db.Model):
    """Model for tracking data imports."""
    __tablename__ = 'import_log'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    import_date = Column(DateTime, default=datetime.utcnow)
    import_type = Column(String(50), nullable=True)  # 'property', 'tax_district', etc.
    records_imported = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    status = Column(String(50), default='completed')  # 'completed', 'failed', 'partial'
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<ImportLog(id={self.id}, filename='{self.filename}', date='{self.import_date}')>"

class ExportLog(db.Model):
    """Model for tracking data exports."""
    __tablename__ = 'export_log'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    export_date = Column(DateTime, default=datetime.utcnow)
    export_type = Column(String(50), nullable=True)  # 'tax_roll', 'compliance_report', etc.
    rows_exported = Column(Integer, default=0)
    status = Column(String(50), default='completed')  # 'completed', 'failed', 'partial'
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<ExportLog(id={self.id}, filename='{self.filename}', date='{self.export_date}')>"

class TaxCodeHistoricalRate(db.Model):
    """
    Model for storing historical tax rates for each tax code over multiple years.
    """
    __tablename__ = 'tax_code_historical_rate'
    
    id = Column(Integer, primary_key=True)
    tax_code_id = Column(Integer, ForeignKey('tax_code.id'), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    levy_rate = Column(Float, nullable=False)
    levy_amount = Column(Float, nullable=True)
    total_assessed_value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tax_code = relationship('TaxCode', back_populates='historical_rates')
    
    # Unique constraint for tax_code_id and year
    __table_args__ = (
        UniqueConstraint('tax_code_id', 'year', name='uix_tax_code_year'),
    )
    
    def __repr__(self):
        return f"<TaxCodeHistoricalRate(tax_code_id={self.tax_code_id}, year={self.year}, rate={self.levy_rate})>"

class ComplianceCheck(db.Model):
    """Model for storing statutory compliance checks."""
    __tablename__ = 'compliance_check'
    
    id = Column(Integer, primary_key=True)
    tax_code_id = Column(Integer, ForeignKey('tax_code.id'), nullable=False, index=True)
    check_date = Column(DateTime, default=datetime.utcnow)
    check_type = Column(String(50), nullable=False)  # 'rate_limit', 'increase_limit', etc.
    is_compliant = Column(Boolean, nullable=False)
    details = Column(Text, nullable=True)
    year = Column(Integer, nullable=False, default=lambda: datetime.now().year)
    
    # Relationships
    tax_code = relationship('TaxCode')
    
    def __repr__(self):
        return f"<ComplianceCheck(id={self.id}, tax_code_id={self.tax_code_id}, compliant={self.is_compliant})>"

class LevyScenario(db.Model):
    """Model for storing levy scenario simulations."""
    __tablename__ = 'levy_scenario'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    base_year = Column(Integer, nullable=False, default=lambda: datetime.now().year)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    adjustments = relationship('LevyScenarioAdjustment', back_populates='scenario', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<LevyScenario(id={self.id}, name='{self.name}')>"

class LevyScenarioAdjustment(db.Model):
    """Model for storing specific adjustments within a levy scenario."""
    __tablename__ = 'levy_scenario_adjustment'
    
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey('levy_scenario.id'), nullable=False)
    tax_code_id = Column(Integer, ForeignKey('tax_code.id'), nullable=False)
    adjustment_type = Column(String(50), nullable=False)  # 'percentage', 'fixed_amount', etc.
    adjustment_value = Column(Float, nullable=False)  # Percentage or amount
    
    # Relationships
    scenario = relationship('LevyScenario', back_populates='adjustments')
    tax_code = relationship('TaxCode')
    
    def __repr__(self):
        return f"<LevyScenarioAdjustment(id={self.id}, tax_code_id={self.tax_code_id}, value={self.adjustment_value})>"