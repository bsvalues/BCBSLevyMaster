"""
Database models for the Levy Calculation System.

This module defines all the database models used in the Levy Calculation System
including property, tax district, tax code, and levy-related entities.
"""

import sqlalchemy.inspection
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app import db


class User(db.Model):
    """User model for authentication and tracking actions."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    role = Column(String(20), default='user')  # admin, assessor, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    audit_logs = relationship('AuditLog', back_populates='user')

    def __repr__(self):
        return f'<User {self.username}>'


class TaxDistrict(db.Model):
    """Tax district model representing a taxing jurisdiction."""
    __tablename__ = 'tax_district'
    
    id = Column(Integer, primary_key=True)
    district_name = Column(String(100), nullable=False)
    district_code = Column(String(20), nullable=False, unique=True, index=True)
    district_type = Column(String(50))  # School, Fire, City, County, etc.
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tax_code_districts = relationship('TaxCodeDistrict', back_populates='district')
    levy_limits = relationship('LevyLimit', back_populates='district')
    
    def __repr__(self):
        return f'<TaxDistrict {self.district_code}: {self.district_name}>'


class TaxCode(db.Model):
    """Tax code model representing a unique combination of tax districts."""
    __tablename__ = 'tax_code'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(20), nullable=False, unique=True, index=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    year = Column(Integer, default=datetime.now().year, nullable=False, index=True)
    total_levy_rate = Column(Float, default=0.0)  # Per $1,000 of assessed value
    total_assessed_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tax_code_districts = relationship('TaxCodeDistrict', back_populates='tax_code')
    properties = relationship('Property', back_populates='tax_code')
    historical_rates = relationship('TaxCodeHistoricalRate', back_populates='tax_code')
    
    __table_args__ = (
        UniqueConstraint('code', 'year', name='uix_code_year'),
    )
    
    def __repr__(self):
        return f'<TaxCode {self.code} ({self.year})>'


class TaxCodeDistrict(db.Model):
    """Junction table for tax codes and districts with levy rates."""
    __tablename__ = 'tax_code_district'
    
    id = Column(Integer, primary_key=True)
    tax_code_id = Column(Integer, ForeignKey('tax_code.id'), nullable=False)
    district_id = Column(Integer, ForeignKey('tax_district.id'), nullable=False)
    levy_rate = Column(Float, default=0.0)  # Per $1,000 of assessed value
    levy_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tax_code = relationship('TaxCode', back_populates='tax_code_districts')
    district = relationship('TaxDistrict', back_populates='tax_code_districts')
    
    __table_args__ = (
        UniqueConstraint('tax_code_id', 'district_id', name='uix_taxcode_district'),
    )
    
    def __repr__(self):
        return f'<TaxCodeDistrict {self.tax_code.code} - {self.district.district_code}>'


class Property(db.Model):
    """Property model representing a real estate property."""
    __tablename__ = 'property'
    
    id = Column(Integer, primary_key=True)
    parcel_id = Column(String(30), nullable=False, unique=True, index=True)
    address = Column(String(200))
    owner_name = Column(String(100))
    assessed_value = Column(Float, default=0.0)
    market_value = Column(Float, default=0.0)
    land_value = Column(Float, default=0.0)
    improvement_value = Column(Float, default=0.0)
    property_class = Column(String(20))  # Residential, Commercial, etc.
    tax_code_id = Column(Integer, ForeignKey('tax_code.id'), nullable=False, index=True)
    year = Column(Integer, default=datetime.now().year, nullable=False, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    lot_size = Column(Float)  # Square feet
    building_size = Column(Float)  # Square feet
    is_exempt = Column(Boolean, default=False)
    exemption_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tax_code = relationship('TaxCode', back_populates='properties')
    exemptions = relationship('PropertyExemption', back_populates='property')
    
    __table_args__ = (
        UniqueConstraint('parcel_id', 'year', name='uix_parcel_year'),
    )
    
    def __repr__(self):
        return f'<Property {self.parcel_id} ({self.year})>'


class PropertyExemption(db.Model):
    """Property exemption model for tracking exemptions applied to properties."""
    __tablename__ = 'property_exemption'
    
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('property.id'), nullable=False, index=True)
    exemption_type = Column(String(50), nullable=False)  # Senior, Veteran, Nonprofit, etc.
    exemption_amount = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    property = relationship('Property', back_populates='exemptions')
    
    def __repr__(self):
        return f'<PropertyExemption {self.exemption_type}: ${self.exemption_amount:,.2f}>'


class LevyLimit(db.Model):
    """Levy limit model for statutory levy limitations."""
    __tablename__ = 'levy_limit'
    
    id = Column(Integer, primary_key=True)
    district_id = Column(Integer, ForeignKey('tax_district.id'), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    limit_type = Column(String(50), nullable=False)  # Statutory, Voted, Banked
    max_rate = Column(Float)  # Per $1,000 of assessed value
    max_amount = Column(Float)
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    district = relationship('TaxDistrict', back_populates='levy_limits')
    
    __table_args__ = (
        UniqueConstraint('district_id', 'year', 'limit_type', name='uix_district_year_limittype'),
    )
    
    def __repr__(self):
        return f'<LevyLimit {self.district.district_code} ({self.year}): {self.limit_type}>'


class TaxCodeHistoricalRate(db.Model):
    """Model for storing historical tax rates for each tax code over multiple years."""
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
    
    __table_args__ = (
        UniqueConstraint('tax_code_id', 'year', name='uix_tax_code_year'),
    )
    
    def __repr__(self):
        return f'<TaxCodeHistoricalRate {self.tax_code.code} ({self.year}): {self.levy_rate}>'


class ImportLog(db.Model):
    """Import log for tracking data imports."""
    __tablename__ = 'import_log'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    import_date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'))
    record_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    import_type = Column(String(50))  # properties, districts, tax_codes, etc.
    import_year = Column(Integer)
    status = Column(String(20))  # completed, failed, partial
    error_log = Column(Text)
    
    def __repr__(self):
        return f'<ImportLog {self.filename} ({self.import_date})>'


class AuditLog(db.Model):
    """Audit log for tracking user actions."""
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String(50), nullable=False)  # create, update, delete, import, export
    table_name = Column(String(50))
    record_id = Column(Integer)
    changes = Column(Text)  # JSON of changes
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(45))
    
    # Relationships
    user = relationship('User', back_populates='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user.username if self.user else "Unknown"} at {self.timestamp}>'


class GlossaryTerm(db.Model):
    """Glossary terms for property tax terminology."""
    __tablename__ = 'glossary_term'
    
    id = Column(Integer, primary_key=True)
    term = Column(String(100), nullable=False, unique=True)
    technical_definition = Column(Text, nullable=False)
    plain_language = Column(Text, nullable=False)
    example = Column(Text)
    category = Column(String(50))  # assessment, levy, exemption
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<GlossaryTerm {self.term}>'


class ComplianceReport(db.Model):
    """Compliance report model for tracking statutory compliance."""
    __tablename__ = 'compliance_report'
    
    id = Column(Integer, primary_key=True)
    report_date = Column(DateTime, default=datetime.utcnow)
    report_year = Column(Integer, nullable=False, index=True)
    report_type = Column(String(50), nullable=False)  # annual, levy, special
    status = Column(String(20), nullable=False)  # draft, submitted, approved
    submitted_by = Column(Integer, ForeignKey('users.id'))
    approved_by = Column(Integer, ForeignKey('users.id'))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ComplianceReport {self.report_type} ({self.report_year}): {self.status}>'


class BillImpactEvaluation(db.Model):
    """Bill impact evaluation for proposed levy changes."""
    __tablename__ = 'bill_impact_evaluation'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    evaluation_date = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'))
    year = Column(Integer, nullable=False, index=True)
    is_approved = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Relationships
    tax_codes = relationship('BillImpactTaxCode', back_populates='evaluation')
    
    def __repr__(self):
        return f'<BillImpactEvaluation {self.name} ({self.year})>'


class BillImpactTaxCode(db.Model):
    """Bill impact details for tax codes in an evaluation."""
    __tablename__ = 'bill_impact_tax_code'
    
    id = Column(Integer, primary_key=True)
    evaluation_id = Column(Integer, ForeignKey('bill_impact_evaluation.id'), nullable=False, index=True)
    tax_code_id = Column(Integer, ForeignKey('tax_code.id'), nullable=False)
    current_rate = Column(Float, nullable=False)
    proposed_rate = Column(Float, nullable=False)
    average_impact_amount = Column(Float)
    average_impact_percent = Column(Float)
    median_property_impact = Column(Float)
    notes = Column(Text)
    
    # Relationships
    evaluation = relationship('BillImpactEvaluation', back_populates='tax_codes')
    
    __table_args__ = (
        UniqueConstraint('evaluation_id', 'tax_code_id', name='uix_eval_taxcode'),
    )
    
    def __repr__(self):
        return f'<BillImpactTaxCode {self.tax_code.code} in {self.evaluation.name}>'


class DataArchive(db.Model):
    """Data archive for long-term storage of levy data."""
    __tablename__ = 'data_archive'
    
    id = Column(Integer, primary_key=True)
    archive_date = Column(DateTime, default=datetime.utcnow)
    archive_type = Column(String(50), nullable=False)  # levy, assessment, collection
    year = Column(Integer, nullable=False, index=True)
    file_path = Column(String(255))
    file_size = Column(Integer)  # In bytes
    is_encrypted = Column(Boolean, default=False)
    checksum = Column(String(64))  # SHA-256 hash
    created_by = Column(Integer, ForeignKey('users.id'))
    notes = Column(Text)
    
    def __repr__(self):
        return f'<DataArchive {self.archive_type} ({self.year})>'