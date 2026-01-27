import os
import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
from dotenv import load_dotenv

from database import User

load_dotenv()

# JWT Configuration
ENVIRONMENT = os.getenv('FLASK_ENV') or os.getenv('ENV') or 'production'
JWT_SECRET = os.getenv('JWT_SECRET')

if not JWT_SECRET:
    if ENVIRONMENT.lower() == 'production':
        raise RuntimeError(
            "JWT_SECRET environment variable must be set in production for secure token signing."
        )
    logging.warning(
        "JWT_SECRET is not set; using a non-secure default secret suitable only for development."
    )
    JWT_SECRET = 'insecure-development-jwt-secret-change-me'
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))


def generate_token(user_id, username, role):
    """Generate JWT token for authenticated user"""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        if not token:
            return jsonify({'error': 'Authentication required', 'code': 'NO_TOKEN'}), 401
        
        # Decode token
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token', 'code': 'INVALID_TOKEN'}), 401
        
        # Verify user still exists and is active
        user = User.get_by_id(payload['user_id'])
        if not user:
            return jsonify({'error': 'User not found', 'code': 'USER_NOT_FOUND'}), 401
        
        # Store user info in flask g object
        g.current_user = {
            'id': payload['user_id'],
            'username': payload['username'],
            'role': payload['role']
        }
        
        return f(*args, **kwargs)
    
    return decorated_function


def admin_required(f):
    """Decorator to require admin role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        if not token:
            return jsonify({'error': 'Authentication required', 'code': 'NO_TOKEN'}), 401
        
        # Decode token
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token', 'code': 'INVALID_TOKEN'}), 401
        
        # Check admin role
        if payload.get('role') != 'admin':
            return jsonify({'error': 'Admin access required', 'code': 'NOT_ADMIN'}), 403
        
        # Verify user still exists and is active
        user = User.get_by_id(payload['user_id'])
        if not user:
            return jsonify({'error': 'User not found', 'code': 'USER_NOT_FOUND'}), 401
        
        # Store user info in flask g object
        g.current_user = {
            'id': payload['user_id'],
            'username': payload['username'],
            'role': payload['role']
        }
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user():
    """Get current authenticated user from flask g object"""
    return getattr(g, 'current_user', None)


class AuthService:
    """Authentication service for handling login/logout"""
    
    @staticmethod
    def login(username, password):
        """Authenticate user and return token"""
        if not username or not password:
            return {'error': 'Username and password are required'}, 400
        
        user = User.verify_password(username, password)
        if not user:
            return {'error': 'Invalid username or password'}, 401
        
        # Update last login
        User.update_last_login(user['id'])
        
        # Generate token
        token = generate_token(user['id'], user['username'], user['role'])
        
        return {
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role']
            }
        }, 200
    
    @staticmethod
    def get_user_info(user_id):
        """Get user information by ID"""
        user = User.get_by_id(user_id)
        if user:
            return {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'created_at': str(user['created_at']) if user['created_at'] else None,
                'last_login': str(user['last_login']) if user['last_login'] else None
            }
        return None
    
    @staticmethod
    def change_password(user_id, current_password, new_password):
        """Change user password"""
        user = User.get_by_id(user_id)
        if not user:
            return {'error': 'User not found'}, 404
        
        # Verify current password
        if not User.verify_password(user['username'], current_password):
            return {'error': 'Current password is incorrect'}, 400
        
        # Validate new password
        if len(new_password) < 6:
            return {'error': 'New password must be at least 6 characters'}, 400
        
        # Update password
        User.update(user_id, password=new_password)
        
        return {'message': 'Password changed successfully'}, 200
