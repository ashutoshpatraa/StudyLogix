"""
StudyLogix — User Manager Service
Handles user registration, authentication, and user data.
"""

import logging
import threading

logger = logging.getLogger(__name__)


class UserManager:
    """Handles user registration and authentication."""

    def __init__(self, db_manager):
        self.db = db_manager
        self.db_lock = threading.Lock()

    def register_user(self, username, password):
        """Register a new user. Returns (success, message)."""
        with self.db_lock:
            cursor = None
            try:
                cursor = self.db.connection.cursor()
                cursor.execute(
                    "SELECT username FROM users WHERE username = ?",
                    (username,),
                )
                if cursor.fetchone():
                    return False, "Username already exists."

                password_hash = self.db.hash_password(password)
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash),
                )
                self.db.connection.commit()
                return True, "Account created successfully!"
            except Exception:
                logger.exception("Error registering user")
                return False, "An unexpected error occurred. Please try again."
            finally:
                if cursor:
                    cursor.close()

    def login_user(self, username, password):
        """Authenticate a user. Returns (success, user_data|None, message)."""
        with self.db_lock:
            cursor = None
            try:
                cursor = self.db.connection.cursor()
                cursor.execute(
                    "SELECT user_id, username, password_hash FROM users WHERE username = ?",
                    (username,),
                )
                user = cursor.fetchone()
                if user and self.db.verify_password(password, user[2]):
                    return True, {"user_id": user[0], "username": user[1]}, "Login successful"
                return False, None, "Invalid username or password."
            except Exception:
                logger.exception("Error during login")
                return False, None, "An unexpected error occurred. Please try again."
            finally:
                if cursor:
                    cursor.close()
