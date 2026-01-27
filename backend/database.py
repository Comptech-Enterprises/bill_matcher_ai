import sqlite3
import os
from datetime import datetime
import bcrypt

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'bill_matcher.db')

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Create sessions table for tracking user sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    
    # Create default admin user if no users exist
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        create_default_admin(conn)
    
    conn.close()

def create_default_admin(conn=None):
    """Create the default admin user"""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True
    
    cursor = conn.cursor()
    
    # Check if admin already exists
    cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone() is None:
        # Hash the default password
        password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, created_at, is_active)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', password_hash.decode('utf-8'), 'admin', datetime.utcnow(), True))
        
        conn.commit()
        print("[AUTH] Default admin user created (username: admin, password: admin123)")
    
    if should_close:
        conn.close()

class User:
    """User model for database operations"""
    
    @staticmethod
    def create(username, password, role='user'):
        """Create a new user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute('''
                INSERT INTO users (username, password_hash, role, created_at, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password_hash.decode('utf-8'), role, datetime.utcnow(), True))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return {'id': user_id, 'username': username, 'role': role}
        except sqlite3.IntegrityError:
            conn.close()
            raise ValueError('Username already exists')
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND is_active = 1', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    @staticmethod
    def verify_password(username, password):
        """Verify user password"""
        user = User.get_by_username(username)
        if user:
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return user
        return None
    
    @staticmethod
    def update_last_login(user_id):
        """Update user's last login timestamp"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.utcnow(), user_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_all():
        """Get all active users"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, role, created_at, last_login, is_active FROM users WHERE is_active = 1')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def update(user_id, username=None, password=None, role=None):
        """Update user details"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if username:
            updates.append('username = ?')
            params.append(username)
        
        if password:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            updates.append('password_hash = ?')
            params.append(password_hash.decode('utf-8'))
        
        if role:
            updates.append('role = ?')
            params.append(role)
        
        if updates:
            params.append(user_id)
            query = f'UPDATE users SET {", ".join(updates)} WHERE id = ?'
            try:
                cursor.execute(query, params)
                conn.commit()
                conn.close()
                return True
            except sqlite3.IntegrityError:
                conn.close()
                raise ValueError('Username already exists')
        
        conn.close()
        return False
    
    @staticmethod
    def delete(user_id):
        """Soft delete a user (set is_active to False)"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0
    
    @staticmethod
    def hard_delete(user_id):
        """Permanently delete a user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0

# Initialize database when module is imported
init_db()
