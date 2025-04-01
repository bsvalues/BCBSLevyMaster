import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from config import config_by_name

class Base(DeclarativeBase):
    """Base class for all database models."""
    pass

# Initialize SQLAlchemy with the Base class
db = SQLAlchemy(model_class=Base)

# Initialize Migration object (will be configured after the app)
migrate = Migrate()

def create_app(config_name=None):
    """
    Application factory function to create and configure the Flask app.
    
    Args:
        config_name: Configuration environment to use (development, testing, production)
        
    Returns:
        The configured Flask application
    """
    # Determine configuration environment
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Create the app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config_by_name[config_name])
    config_by_name[config_name].init_app(app)
    
    # Configure logging
    logging.basicConfig(
        level=app.config.get('LOG_LEVEL', logging.INFO),
        format=app.config.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Initialize the app with extensions
    db.init_app(app)
    
    # Import models before initializing migrations
    with app.app_context():
        import models
    
    # Initialize Flask-Migrate
    migrate.init_app(app, db, directory=app.config.get('MIGRATION_DIR'))
    
    # Register blueprints
    from routes2 import main_bp
    app.register_blueprint(main_bp)
    
    # In development mode, create all tables using db.create_all()
    # In production, migrations should be used
    if config_name != 'production':
        with app.app_context():
            # Only call create_all in development/testing environments
            # In production, migrations should be used instead
            db.create_all()
    
    return app