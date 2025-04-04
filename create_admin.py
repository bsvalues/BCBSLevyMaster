#!/usr/bin/env python3
"""
Create admin user utility for the Levy Calculation System.

This script creates an admin user if one doesn't already exist.

Usage:
    python create_admin.py [options]

Options:
    --username, -u USERNAME    Admin username (default: admin)
    --email, -e EMAIL          Admin email (default: admin@example.com)
    --password, -p PASSWORD    Admin password (default: admin123)
    --first-name, -f NAME      Admin first name (optional)
    --last-name, -l NAME       Admin last name (optional)
    --force                    Create admin even if users already exist
    --check                    Just check if admin user exists

Examples:
    # Create default admin user
    python create_admin.py

    # Create custom admin user
    python create_admin.py -u myadmin -e admin@org.com -p secure123 -f John -l Doe

    # Create admin user even if users exist
    python create_admin.py --force
"""

import argparse
import logging
import os
import sys
from flask import Flask

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_admin_user(username, email, password, first_name=None, last_name=None, force=False):
    """
    Create an admin user with the specified credentials.
    
    Args:
        username: Admin username
        email: Admin email
        password: Admin password
        first_name: Admin first name (optional)
        last_name: Admin last name (optional)
        force: Create admin even if users already exist
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Import here to avoid import errors
    from utils.auth_utils import create_user
    from models import User
    
    try:
        # Check if users already exist
        if not force and User.query.first() is not None:
            return False, "Users already exist. Use --force to create admin anyway."
        
        # Check if username already exists
        if User.query.filter_by(username=username).first() is not None:
            return False, f"Username '{username}' already exists."
        
        # Check if email already exists
        if User.query.filter_by(email=email).first() is not None:
            return False, f"Email '{email}' already exists."
        
        # Create admin user
        success, result = create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_admin=True
        )
        
        if success:
            logger.info(f"Admin user '{result.username}' created successfully.")
            return True, f"Admin user '{result.username}' created successfully."
        else:
            logger.error(f"Failed to create admin user: {result}")
            return False, f"Failed to create admin user: {result}"
        
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        return False, f"Error creating admin user: {str(e)}"


def check_admin_users():
    """
    Check if any admin users exist.
    
    Returns:
        Tuple of (admin_exists: bool, user_count: int, admin_count: int)
    """
    # Import here to avoid import errors
    from models import User
    
    try:
        user_count = User.query.count()
        admin_count = User.query.filter_by(is_admin=True).count()
        
        return admin_count > 0, user_count, admin_count
    except Exception as e:
        logger.error(f"Error checking admin users: {str(e)}")
        return False, 0, 0


def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Create admin user for the Levy Calculation System.')
    parser.add_argument('-u', '--username', default='admin', help='Admin username')
    parser.add_argument('-e', '--email', default='admin@example.com', help='Admin email')
    parser.add_argument('-p', '--password', default='admin123', help='Admin password')
    parser.add_argument('-f', '--first-name', help='Admin first name')
    parser.add_argument('-l', '--last-name', help='Admin last name')
    parser.add_argument('--force', action='store_true', help='Create admin even if users already exist')
    parser.add_argument('--check', action='store_true', help='Just check if admin user exists')
    
    args = parser.parse_args()
    
    # Create Flask app
    from app import create_app
    app = create_app()
    
    with app.app_context():
        if args.check:
            # Check if admin users exist
            admin_exists, user_count, admin_count = check_admin_users()
            
            logger.info(f"Total users: {user_count}")
            logger.info(f"Admin users: {admin_count}")
            
            if admin_exists:
                logger.info("Admin user(s) already exist.")
                return 0
            else:
                logger.info("No admin users found.")
                return 1
        else:
            # Create admin user
            success, message = create_admin_user(
                username=args.username,
                email=args.email,
                password=args.password,
                first_name=args.first_name,
                last_name=args.last_name,
                force=args.force
            )
            
            if success:
                logger.info(message)
                return 0
            else:
                logger.error(message)
                return 1


if __name__ == '__main__':
    sys.exit(main())