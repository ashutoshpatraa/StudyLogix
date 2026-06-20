"""
StudyLogix — Database Manager
Handles SQLite database connection, table creation, and password hashing.
"""

import logging
import sqlite3

import bcrypt

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages the SQLite database lifecycle and password operations."""

    def __init__(self, db_file='study_tracker.db'):
        self.db_file = db_file
        self.connection = None

    def connect(self):
        """Establish a database connection."""
        try:
            self.connection = sqlite3.connect(self.db_file, check_same_thread=False)
            self.connection.execute("PRAGMA foreign_keys = ON")
            logger.info("Connected to SQLite database: %s", self.db_file)
            return True
        except sqlite3.Error:
            logger.exception("Error connecting to SQLite database")
            return False

    def create_tables(self):
        """Create all required tables if they do not exist."""
        if not self.connection:
            if not self.connect():
                return False

        cursor = self.connection.cursor()

        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    password_hash BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
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
            """)

            cursor.execute("""
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
            """)

            cursor.execute("""
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
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS friendships (
                    friendship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    friend_id INTEGER NOT NULL,
                    status TEXT CHECK(status IN ('pending', 'accepted', 'rejected', 'blocked')) DEFAULT 'pending',
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    responded_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (friend_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    UNIQUE(user_id, friend_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS study_groups (
                    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_name TEXT NOT NULL,
                    created_by INTEGER NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_members (
                    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT CHECK(role IN ('admin', 'member')) DEFAULT 'member',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES study_groups(group_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    UNIQUE(group_id, user_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_timers (
                    timer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    time_remaining INTEGER NOT NULL,
                    is_break INTEGER DEFAULT 0,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (session_id) REFERENCES pomodoro_sessions(session_id) ON DELETE CASCADE
                )
            """)

            self.connection.commit()
            logger.info("All database tables created successfully")
            return True

        except sqlite3.Error:
            logger.exception("Error creating database tables")
            return False
        finally:
            cursor.close()

    def hash_password(self, password):
        """Hash a plaintext password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    def verify_password(self, password, hashed):
        """Verify a plaintext password against a bcrypt hash."""
        if isinstance(hashed, str):
            hashed = hashed.encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), hashed)

    def close_connection(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")


def initialize_database():
    """Create a DatabaseManager, connect, and ensure tables exist."""
    db = DatabaseManager()
    if db.connect():
        if db.create_tables():
            return db
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("🚀 Testing SQLite Database...")
    db = initialize_database()
    if db:
        print("🎉 SQLite database setup successful!")
        db.close_connection()
    else:
        print("❌ SQLite database setup failed!")
