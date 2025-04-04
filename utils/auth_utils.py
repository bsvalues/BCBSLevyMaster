"""
Authentication utilities for the Levy Calculation System.

This module provides utilities for user authentication, including:
- Password hashing and verification
- User registration
- User login and logout
"""

import logging
from datetime import datetime
from typing import Tuple, Union

from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import User


logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    Hash a password using Werkzeug's implementation of pbkdf2.
    
    Args:
        password: The password to hash
        
    Returns:
        The hashed password string
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    return generate_password_hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        password: The password to verify
        hashed_password: The hashed password to verify against
        
    Returns:
        True if the password matches the hash, False otherwise
    """
    if not password or not hashed_password:
        return False
    
    return check_password_hash(hashed_password, password)


def create_user(username: str, email: str, password: str, first_name: str = None, 
                last_name: str = None, is_admin: bool = False) -> Tuple[bool, Union[User, str]]:
    """
    Create a new user in the database.
    
    Args:
        username: Username (unique)
        email: Email address (unique)
        password: Password (will be hashed)
        first_name: First name (optional)
        last_name: Last name (optional)
        is_admin: Whether the user is an admin (default: False)
        
    Returns:
        Tuple of (success: bool, user_or_error_message: Union[User, str])
    """
    try:
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            if existing_user.username == username:
                return False, f"Username '{username}' is already taken"
            else:
                return False, f"Email '{email}' is already registered"
        
        # Create new user
        hashed_password = hash_password(password)
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"Created user: {username}")
        return True, user
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating user: {str(e)}")
        return False, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user: {str(e)}")
        return False, f"Error: {str(e)}"


def authenticate_user(username_or_email: str, password: str) -> Tuple[bool, Union[User, str]]:
    """
    Authenticate a user with username/email and password.
    
    Args:
        username_or_email: Username or email address
        password: Password to verify
        
    Returns:
        Tuple of (success: bool, user_or_error_message: Union[User, str])
    """
    try:
        # Find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if not user:
            return False, "Invalid username or email"
        
        if not user.is_active:
            return False, "Account is inactive"
        
        # Verify password
        if not verify_password(password, user.password_hash):
            return False, "Invalid password"
        
        # Update last login time
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return True, user
    
    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        return False, f"Authentication error: {str(e)}"


def update_user_password(user_id: int, current_password: str, new_password: str) -> Tuple[bool, str]:
    """
    Update a user's password.
    
    Args:
        user_id: User ID
        current_password: Current password for verification
        new_password: New password to set
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            return False, "Current password is incorrect"
        
        # Update password
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Password updated for user: {user.username}")
        return True, "Password updated successfully"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating password: {str(e)}")
        return False, f"Error updating password: {str(e)}"


def update_user_profile(user_id: int, email: str = None, first_name: str = None, 
                      last_name: str = None) -> Tuple[bool, Union[User, str]]:
    """
    Update a user's profile information.
    
    Args:
        user_id: User ID
        email: New email address (optional)
        first_name: New first name (optional)
        last_name: New last name (optional)
        
    Returns:
        Tuple of (success: bool, user_or_error_message: Union[User, str])
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"
        
        # Update email if provided and different
        if email and email != user.email:
            # Check if email is already taken
            existing_user = User.query.filter(User.email == email).first()
            if existing_user and existing_user.id != user_id:
                return False, f"Email '{email}' is already registered"
            
            user.email = email
        
        # Update name fields if provided
        if first_name is not None:
            user.first_name = first_name
        
        if last_name is not None:
            user.last_name = last_name
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Profile updated for user: {user.username}")
        return True, user
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile: {str(e)}")
        return False, f"Error updating profile: {str(e)}"


def create_admin_user_if_none_exists() -> None:
    """
    Create an admin user if no users exist in the database.
    This is used for initial setup of the application.
    
    Default admin credentials:
    - Username: admin
    - Email: admin@example.com
    - Password: admin123
    """
    # Check if any user exists
    if User.query.first() is None:
        default_password = current_app.config.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
        success, result = create_user(
            username="admin",
            email="admin@example.com",
            password=default_password,
            first_name="Admin",
            last_name="User",
            is_admin=True
        )
        
        if success:
            logger.info(f"Created default admin user: {result.username}")
        else:
            logger.error(f"Failed to create default admin user: {result}")