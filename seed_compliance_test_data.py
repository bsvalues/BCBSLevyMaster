"""
Script to seed the database with test compliance data.
"""
from app import app
from utils.test_compliance_data import generate_test_compliance_data

if __name__ == "__main__":
    with app.app_context():
        print("Generating test compliance data...")
        result = generate_test_compliance_data()
        print(f"Result: {result}")