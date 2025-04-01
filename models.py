from datetime import datetime
import json
from sqlalchemy.inspection import inspect
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
    
    # Relationship to historical rates
    historical_rates = db.relationship('TaxCodeHistoricalRate', backref='tax_code', lazy='dynamic',
                                      cascade='all, delete-orphan')
    
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

class TaxCodeHistoricalRate(db.Model):
    """
    Model for storing historical tax rates for each tax code over multiple years.
    """
    id = db.Column(db.Integer, primary_key=True)
    tax_code_id = db.Column(db.Integer, db.ForeignKey('tax_code.id'), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    levy_rate = db.Column(db.Float, nullable=False)
    levy_amount = db.Column(db.Float, nullable=True)
    total_assessed_value = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure uniqueness of tax_code_id and year combination
    __table_args__ = (
        db.UniqueConstraint('tax_code_id', 'year', name='uix_tax_code_year'),
    )
    
    def __repr__(self):
        return f"<TaxCodeHistoricalRate {self.tax_code_id}-{self.year}>"

class BillImpactEvaluation(db.Model):
    """
    Model for storing bill impact evaluation scenarios for proposed legislation.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(50), default='draft')  # draft, active, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tax_codes = db.relationship('BillImpactTaxCode', backref='evaluation', lazy='dynamic',
                               cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<BillImpactEvaluation {self.name}>"

class BillImpactTaxCode(db.Model):
    """
    Model for storing tax code specific changes for a bill impact evaluation.
    """
    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('bill_impact_evaluation.id'), nullable=False)
    tax_code = db.Column(db.String(20), nullable=False)
    current_rate = db.Column(db.Float, nullable=False)
    proposed_rate = db.Column(db.Float, nullable=False)
    percent_change = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<BillImpactTaxCode {self.tax_code}>"

class AuditLog(db.Model):
    """
    Model for tracking changes to records in the system.
    """
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(255), nullable=False, index=True)
    record_id = db.Column(db.Integer, nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)  # CREATE, UPDATE, DELETE
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, nullable=True)  # Optional user ID if authentication is implemented
    old_values = db.Column(db.Text, nullable=True)  # JSON string of old values
    new_values = db.Column(db.Text, nullable=True)  # JSON string of new values
    ip_address = db.Column(db.String(50), nullable=True)
    
    def __repr__(self):
        return f"<AuditLog {self.table_name}:{self.record_id} {self.action}>"
    
    @classmethod
    def log_change(cls, table_name, record_id, action, old_values=None, new_values=None, user_id=None, ip_address=None):
        """
        Create an audit log entry for a database change.
        
        Args:
            table_name: The name of the table being modified
            record_id: The ID of the record being modified
            action: CREATE, UPDATE, or DELETE
            old_values: Dictionary of values before change (for UPDATE/DELETE)
            new_values: Dictionary of values after change (for CREATE/UPDATE)
            user_id: Optional ID of user making the change
            ip_address: Optional IP address of user making the change
            
        Returns:
            The created AuditLog instance
        """
        # Convert dictionaries to JSON strings
        old_values_json = json.dumps(old_values) if old_values else None
        new_values_json = json.dumps(new_values) if new_values else None
        
        # Create the audit log entry
        log_entry = cls(
            table_name=table_name,
            record_id=record_id,
            action=action,
            old_values=old_values_json,
            new_values=new_values_json,
            user_id=user_id,
            ip_address=ip_address
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
        return log_entry
    
    def get_old_values(self):
        """Parse and return old values as dictionary."""
        if self.old_values:
            return json.loads(self.old_values)
        return {}
    
    def get_new_values(self):
        """Parse and return new values as dictionary."""
        if self.new_values:
            return json.loads(self.new_values)
        return {}
    
    def get_changes(self):
        """
        Compare old and new values to identify what changed.
        
        Returns:
            Dictionary of changes with field names as keys and tuples of (old_value, new_value) as values
        """
        old = self.get_old_values()
        new = self.get_new_values()
        
        changes = {}
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            
            if old_val != new_val:
                changes[key] = (old_val, new_val)
                
        return changes
        
        
class ForecastModel(db.Model):
    """
    Model for storing tax rate forecasts.
    """
    id = db.Column(db.Integer, primary_key=True)
    tax_code = db.Column(db.String(20), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    model_type = db.Column(db.String(50), nullable=False)  # 'linear', 'exponential', 'arima'
    scenario = db.Column(db.String(50), nullable=False, default='baseline')  # 'baseline', 'optimistic', 'pessimistic'
    years_ahead = db.Column(db.Integer, nullable=False)
    base_year = db.Column(db.Integer, nullable=False)
    historical_data = db.Column(db.Text, nullable=False)  # JSON string of historical years and rates
    forecast_data = db.Column(db.Text, nullable=False)  # JSON string of forecast results
    metrics = db.Column(db.Text, nullable=True)  # JSON string of accuracy metrics
    is_published = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, nullable=True)  # Optional user ID
    
    def __repr__(self):
        return f"<ForecastModel {self.tax_code} {self.scenario}>"
    
    def get_historical_data(self):
        """Parse and return historical data."""
        return json.loads(self.historical_data)
    
    def get_forecast_data(self):
        """Parse and return forecast data."""
        return json.loads(self.forecast_data)
    
    def get_metrics(self):
        """Parse and return accuracy metrics."""
        if self.metrics:
            return json.loads(self.metrics)
        return {}


class DistrictForecast(db.Model):
    """
    Model for storing district-level forecasts.
    """
    id = db.Column(db.Integer, primary_key=True)
    district_id = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    model_type = db.Column(db.String(50), nullable=False)  # 'linear', 'exponential', 'arima'
    scenario = db.Column(db.String(50), nullable=False, default='baseline')
    years_ahead = db.Column(db.Integer, nullable=False)
    base_year = db.Column(db.Integer, nullable=False)
    tax_codes = db.Column(db.Text, nullable=False)  # JSON array of tax codes included in the forecast
    aggregate_forecast = db.Column(db.Text, nullable=False)  # JSON string of aggregate forecast results
    is_published = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, nullable=True)  # Optional user ID
    
    def __repr__(self):
        return f"<DistrictForecast {self.district_id} {self.scenario}>"
    
    def get_tax_codes(self):
        """Parse and return tax codes list."""
        return json.loads(self.tax_codes)
    
    def get_aggregate_forecast(self):
        """Parse and return aggregate forecast data."""
        return json.loads(self.aggregate_forecast)


class ReportTemplate(db.Model):
    """
    Model for storing report templates.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'property', 'tax_code', 'district'
    sections = db.Column(db.Text, nullable=False)  # JSON string of section configurations
    sorting = db.Column(db.Text, nullable=True)  # JSON string of sorting configuration
    filters = db.Column(db.Text, nullable=True)  # JSON string of filter configurations
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, nullable=True)  # Optional user ID
    is_public = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f"<ReportTemplate {self.name}>"
    
    def get_sections(self):
        """Parse and return sections configuration."""
        return json.loads(self.sections)
    
    def get_sorting(self):
        """Parse and return sorting configuration."""
        if self.sorting:
            return json.loads(self.sorting)
        return None
    
    def get_filters(self):
        """Parse and return filters configuration."""
        if self.filters:
            return json.loads(self.filters)
        return []


class ScheduledReport(db.Model):
    """
    Model for storing scheduled report configurations.
    """
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('report_template.id'), nullable=False)
    format = db.Column(db.String(50), nullable=False)  # 'excel', 'pdf', 'csv', 'json'
    frequency = db.Column(db.String(50), nullable=False)  # 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'
    day = db.Column(db.String(50), nullable=True)  # Day of week for weekly reports
    time = db.Column(db.String(50), nullable=True)  # Time of day for execution
    recipients = db.Column(db.Text, nullable=True)  # JSON array of email addresses
    subject = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, nullable=True)  # Optional user ID
    last_run = db.Column(db.DateTime, nullable=True)
    next_run = db.Column(db.DateTime, nullable=True)
    
    # Relationship to template
    template = db.relationship('ReportTemplate', backref='scheduled_reports')
    
    def __repr__(self):
        return f"<ScheduledReport {self.id} {self.frequency}>"
    
    def get_recipients(self):
        """Parse and return recipients list."""
        if self.recipients:
            return json.loads(self.recipients)
        return []

class DataArchive(db.Model):
    """
    Model for storing archived data snapshots with retention policies.
    """
    id = db.Column(db.Integer, primary_key=True)
    archive_type = db.Column(db.String(50), nullable=False, index=True)  # 'backup', 'year_end', 'quarterly', etc.
    table_name = db.Column(db.String(255), nullable=False, index=True)
    archive_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    retention_date = db.Column(db.DateTime, nullable=True, index=True)  # When to delete this archive
    data = db.Column(db.Text, nullable=False)  # JSON string of archived data
    record_count = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.Integer, nullable=True)  # Optional user ID
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='active')  # active, expired
    
    def __repr__(self):
        return f"<DataArchive {self.table_name} {self.archive_date}>"
    
    def get_data(self):
        """Parse and return archived data."""
        return json.loads(self.data)
    
    @classmethod
    def create_archive(cls, table_name, data, archive_type='backup', retention_days=None, 
                      created_by=None, description=None):
        """
        Create a data archive entry.
        
        Args:
            table_name: The name of the table being archived
            data: List of dictionaries containing the data to archive
            archive_type: Type of archive (backup, year_end, quarterly, etc.)
            retention_days: Number of days to retain the archive (None for permanent)
            created_by: Optional ID of user creating the archive
            description: Optional description of the archive
            
        Returns:
            The created DataArchive instance
        """
        # Calculate retention date if specified
        retention_date = None
        if retention_days:
            from datetime import timedelta
            retention_date = datetime.utcnow() + timedelta(days=retention_days)
        
        # Create archive
        archive = cls(
            table_name=table_name,
            archive_type=archive_type,
            retention_date=retention_date,
            data=json.dumps(data),
            record_count=len(data),
            created_by=created_by,
            description=description
        )
        
        db.session.add(archive)
        db.session.commit()
        
        return archive

class ComplianceReport(db.Model):
    """
    Model for storing comprehensive statutory compliance reports.
    """
    id = db.Column(db.Integer, primary_key=True)
    report_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    report_type = db.Column(db.String(50), nullable=False, index=True)  # 'statutory', 'filing', 'banked_capacity'
    year = db.Column(db.Integer, nullable=False, index=True)
    overall_compliant = db.Column(db.Boolean, nullable=False)
    compliance_percentage = db.Column(db.Float, nullable=True)
    critical_issues = db.Column(db.Text, nullable=True)  # JSON string of critical issues
    report_data = db.Column(db.Text, nullable=False)  # JSON string of the full report
    created_by = db.Column(db.Integer, nullable=True)  # Optional user ID
    
    def __repr__(self):
        return f"<ComplianceReport {self.report_type} {self.report_date}>"
    
    def get_report_data(self):
        """Parse and return report data."""
        return json.loads(self.report_data)
    
    def get_critical_issues(self):
        """Parse and return critical issues."""
        if self.critical_issues:
            return json.loads(self.critical_issues)
        return []
