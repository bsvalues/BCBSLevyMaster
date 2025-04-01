"""
Initialize database with tables from models.py.
"""
from app2 import create_app, db

app = create_app()

with app.app_context():
    print("Creating all database tables...")
    db.create_all()
    print("Database tables created successfully.")