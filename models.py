"""
Database models for the Levy Calculation System.

This module defines the data models used throughout the application,
including tax districts, tax codes, levy rates, and user data.
"""

import enum
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

from sqlalchemy import (
    Column, Integer, Float, String, Text, Boolean, DateTime, ForeignKey, 
    UniqueConstraint, Enum, JSON, CheckConstraint, Table
)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, backref
from flask_login import UserMixin

from main import db

# Association tables for many-to-many relationships
property_tax_code_association = Table(
    'property_tax_code_association',
    db.Model.metadata,
    Column('property_id', Integer, ForeignKey('property.id'), primary_key=True),
    Column('tax_code_id', Integer, ForeignKey('tax_code.id'), primary_key=True)
)

tax_code_district_association = Table(
    'tax_code_district_association',
    db.Model.metadata,
    Column('tax_code_id', Integer, ForeignKey('tax_code.id'), primary_key=True),
    Column('tax_district_id', Integer, ForeignKey('tax_district.id'), primary_key=True),
    Column('percentage', Float, nullable=False, default=100.0)
)


class User(UserMixin, db.Model):
    """
    User model for authentication and authorization.
    """
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    first_name = Column(String(64))
    last_name = Column(String(64))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    audit_logs = relationship('AuditLog', back_populates='user')
    import_logs = relationship('ImportLog', back_populates='user')
    export_logs = relationship('ExportLog', back_populates='user')
    
    def __repr__(self):
        return f'<User {self.username}>'


class ImportType(enum.Enum):
    """
    Types of data imports supported by the system.
    """
    TAX_DISTRICT = 'tax_district'
    TAX_CODE = 'tax_code'
    PROPERTY = 'property'
    ASSESSED_VALUE = 'assessed_value'
    LEVY_RATE = 'levy_rate'


class ImportLog(db.Model):
    """
    Records of data imports into the system.
    """
    __tablename__ = 'import_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    import_type = Column(Enum(ImportType), nullable=False)
    file_size = Column(Integer)
    record_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_messages = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    year = Column(Integer, nullable=False, index=True)
    
    # Relationships
    user = relationship('User', back_populates='import_logs')
    
    def __repr__(self):
        return f'<ImportLog {self.filename} ({self.import_type})>'


class ExportLog(db.Model):
    """
    Records of data exports from the system.
    """
    __tablename__ = 'export_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    record_count = Column(Integer, default=0)
    file_size = Column(Integer)
    parameters = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    year = Column(Integer, nullable=False, index=True)
    
    # Relationships
    user = relationship('User', back_populates='export_logs')
    
    def __repr__(self):
        return f'<ExportLog {self.filename}>'


class TaxDistrict(db.Model):
    """
    Taxing districts such as counties, cities, school districts, etc.
    """
    __tablename__ = 'tax_district'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    code = Column(String(32), nullable=False, unique=True, index=True)
    district_type = Column(String(50), nullable=False, index=True)
    statutory_limit = Column(Float)
    is_active = Column(Boolean, default=True)
    county = Column(String(64), nullable=False, index=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    year = Column(Integer, nullable=False, index=True)
    
    # Relationships
    tax_codes = relationship(
        'TaxCode',
        secondary=tax_code_district_association,
        back_populates='tax_districts'
    )
    levy_rates = relationship('LevyRate', back_populates='tax_district')
    
    def __repr__(self):
        return f'<TaxDistrict {self.code} ({self.name})>'


class TaxCode(db.Model):
    """
    Tax codes that define unique combinations of taxing districts.
    """
    __tablename__ = 'tax_code'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(32), nullable=False, index=True)
    description = Column(Text)
    total_rate = Column(Float, default=0.0)
    total_assessed_value = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    year = Column(Integer, nullable=False, index=True)
    
    # Relationships
    tax_districts = relationship(
        'TaxDistrict',
        secondary=tax_code_district_association,
        back_populates='tax_codes'
    )
    properties = relationship(
        'Property',
        secondary=property_tax_code_association,
        back_populates='tax_codes'
    )
    historical_rates = relationship('TaxCodeHistoricalRate', back_populates='tax_code')
    
    __table_args__ = (
        UniqueConstraint('code', 'year', name='uix_tax_code_year'),
    )
    
    def __repr__(self):
        return f'<TaxCode {self.code} ({self.year})>'


class TaxCodeHistoricalRate(db.Model):
    """
    Historical tax rates for each tax code over multiple years.
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
    
    __table_args__ = (
        UniqueConstraint('tax_code_id', 'year', name='uix_tax_code_historical_year'),
    )
    
    def __repr__(self):
        return f'<TaxCodeHistoricalRate {self.tax_code.code} ({self.year}): {self.levy_rate}>'


class Property(db.Model):
    """
    Property records with assessed values and tax information.
    """
    __tablename__ = 'property'
    
    id = Column(Integer, primary_key=True)
    parcel_id = Column(String(64), nullable=False, unique=True, index=True)
    address = Column(String(255))
    owner_name = Column(String(128))
    property_type = Column(String(50), index=True)
    assessed_value = Column(Float, default=0.0)
    market_value = Column(Float, default=0.0)
    land_value = Column(Float, default=0.0)
    improvement_value = Column(Float, default=0.0)
    exemption_amount = Column(Float, default=0.0)
    net_assessed_value = Column(Float, default=0.0)
    is_exempt = Column(Boolean, default=False)
    exemption_type = Column(String(50))
    county = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    year = Column(Integer, nullable=False, index=True)
    
    # Relationships
    tax_codes = relationship(
        'TaxCode',
        secondary=property_tax_code_association,
        back_populates='properties'
    )
    
    def __repr__(self):
        return f'<Property {self.parcel_id}>'


class LevyRate(db.Model):
    """
    Levy rates for taxing districts.
    """
    __tablename__ = 'levy_rate'
    
    id = Column(Integer, primary_key=True)
    tax_district_id = Column(Integer, ForeignKey('tax_district.id'), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    rate = Column(Float, nullable=False)
    levy_amount = Column(Float, nullable=False)
    assessed_value = Column(Float, nullable=False)
    prior_year_rate = Column(Float)
    prior_year_amount = Column(Float)
    rate_change = Column(Float)
    amount_change = Column(Float)
    is_statutory_limit_applied = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tax_district = relationship('TaxDistrict', back_populates='levy_rates')
    
    __table_args__ = (
        UniqueConstraint('tax_district_id', 'year', name='uix_district_levy_year'),
    )
    
    def __repr__(self):
        return f'<LevyRate {self.tax_district.code} ({self.year}): {self.rate}>'


class LevyScenario(db.Model):
    """
    Levy calculation scenarios for what-if analysis.
    """
    __tablename__ = 'levy_scenario'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    base_year = Column(Integer, nullable=False)
    target_year = Column(Integer, nullable=False)
    assumptions = Column(JSON)
    results = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<LevyScenario {self.name}>'


class ForecastModel(db.Model):
    """
    Forecast models and predictions for levy planning.
    """
    __tablename__ = 'forecast_model'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    model_type = Column(String(50), nullable=False)
    parameters = Column(JSON)
    accuracy_metrics = Column(JSON)
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    forecast_years = Column(Integer, nullable=False)
    results = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ForecastModel {self.name}>'


class AuditLog(db.Model):
    """
    Audit trail for system activities.
    """
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    action = Column(String(64), nullable=False)
    table_name = Column(String(64))
    record_id = Column(Integer)
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String(45))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship('User', back_populates='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user.username} at {self.timestamp}>'


class ComplianceReport(db.Model):
    """
    Reports for statutory compliance checks.
    """
    __tablename__ = 'compliance_report'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    report_date = Column(DateTime, default=datetime.utcnow)
    year = Column(Integer, nullable=False, index=True)
    report_type = Column(String(64), nullable=False)
    results = Column(JSON)
    violations_count = Column(Integer, default=0)
    warnings_count = Column(Integer, default=0)
    notes = Column(Text)
    
    def __repr__(self):
        return f'<ComplianceReport {self.report_type} for {self.year}>'


class DataArchive(db.Model):
    """
    Archives of yearly levy data.
    """
    __tablename__ = 'data_archive'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    archive_date = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    tax_districts_count = Column(Integer)
    tax_codes_count = Column(Integer)
    properties_count = Column(Integer)
    total_assessed_value = Column(Float)
    total_levy_amount = Column(Float)
    archive_data = Column(JSON)
    
    def __repr__(self):
        return f'<DataArchive {self.year}>'


class AIAnalysis(db.Model):
    """
    AI-generated analysis and insights.
    """
    __tablename__ = 'ai_analysis'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    analysis_type = Column(String(64), nullable=False)
    query = Column(Text, nullable=False)
    result = Column(Text)
    parameters = Column(JSON)
    model_used = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)
    year = Column(Integer, nullable=False, index=True)
    
    def __repr__(self):
        return f'<AIAnalysis {self.analysis_type} at {self.created_at}>'


class BillImpactEvaluation(db.Model):
    """
    Impact evaluations for property tax bills.
    """
    __tablename__ = 'bill_impact_evaluation'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    base_year = Column(Integer, nullable=False)
    target_year = Column(Integer, nullable=False)
    parameters = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tax_codes = relationship('BillImpactTaxCode', back_populates='evaluation')
    
    def __repr__(self):
        return f'<BillImpactEvaluation {self.name}>'


class BillImpactTaxCode(db.Model):
    """
    Tax code specific results for bill impact evaluations.
    """
    __tablename__ = 'bill_impact_tax_code'
    
    id = Column(Integer, primary_key=True)
    evaluation_id = Column(Integer, ForeignKey('bill_impact_evaluation.id'), nullable=False)
    tax_code_id = Column(Integer, ForeignKey('tax_code.id'), nullable=False)
    base_rate = Column(Float, nullable=False)
    target_rate = Column(Float, nullable=False)
    rate_change = Column(Float)
    rate_change_percent = Column(Float)
    average_bill_change = Column(Float)
    median_bill_change = Column(Float)
    max_bill_change = Column(Float)
    property_count = Column(Integer)
    results = Column(JSON)
    
    # Relationships
    evaluation = relationship('BillImpactEvaluation', back_populates='tax_codes')
    
    def __repr__(self):
        return f'<BillImpactTaxCode for {self.tax_code_id} in {self.evaluation.name}>'


class GlossaryTerm(db.Model):
    """
    Glossary of tax and levy terminology.
    """
    __tablename__ = 'glossary_term'
    
    id = Column(Integer, primary_key=True)
    term = Column(String(128), nullable=False, unique=True)
    definition = Column(Text, nullable=False)
    category = Column(String(64), index=True)
    source = Column(String(255))
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<GlossaryTerm {self.term}>'