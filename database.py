import sqlite3
import bcrypt
import os
from datetime import datetime, timedelta

class DatabaseManager:
    def __init__(self, db_file='study_tracker.db'):
        """
        Initialize SQLite database connection
        """
        self.db_file = db_file
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = sqlite3.connect(self.db_file, check_same_thread=False)
            self.connection.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
            print(f"✅ Connected to SQLite database: {self.db_file}")
            return True
        except sqlite3.Error as e:
            print(f"❌ Error connecting to SQLite: {e}")
            return False
    
    def create_tables(self):
        """Create all required tables"""
        if not self.connection:
            if not self.connect():
                return False
        
        cursor = self.connection.cursor()
        
        try:
            # Create users table
            users_table = """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(users_table)
            
            # Create study_sessions table
            study_sessions_table = """
            CREATE TABLE IF NOT EXISTS study_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                mood TEXT CHECK(mood IN ('excellent', 'good', 'fair', 'poor')) NOT NULL,
                productivity TEXT CHECK(productivity IN ('very_high', 'high', 'medium', 'low', 'very_low')) NOT NULL,
                notes TEXT,
                session_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
            cursor.execute(study_sessions_table)
            
            # Create study_goals table
            study_goals_table = """
            CREATE TABLE IF NOT EXISTS study_goals (
                goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                weekly_target_minutes INTEGER NOT NULL,
                week_start_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, subject, week_start_date)
            )
            """
            cursor.execute(study_goals_table)
            
            # Create pomodoro_sessions table
            pomodoro_sessions_table = """
            CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                duration_minutes INTEGER DEFAULT 25,
                status TEXT CHECK(status IN ('active', 'completed', 'cancelled')) DEFAULT 'active',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
            cursor.execute(pomodoro_sessions_table)
            
            self.connection.commit()
            print("✅ All tables created successfully!")
            return True
            
        except sqlite3.Error as e:
            print(f"❌ Error creating tables: {e}")
            return False
        finally:
            cursor.close()
    
    def hash_password(self, password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    def verify_password(self, password, hashed):
        """Verify password against hash"""
        if isinstance(hashed, str):
            hashed = hashed.encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    
    def close_connection(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("✅ Database connection closed")

# Initialize database
def initialize_database():
    """Initialize database and create tables"""
    db = DatabaseManager()
    
    # Connect and create tables
    if db.connect():
        if db.create_tables():
            return db
    return None

if __name__ == "__main__":
    # Test database connection and table creation
    print("🚀 Testing SQLite Database...")
    db = initialize_database()
    if db:
        print("🎉 SQLite database setup successful!")
        db.close_connection()
    else:
        print("❌ SQLite database setup failed!")
