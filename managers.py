from database import DatabaseManager
import sqlite3
from datetime import date, timedelta

class UserManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def register_user(self, username, email, password):
        """Register a new user"""
        try:
            cursor = self.db.connection.cursor()
            
            # Check if username or email already exists
            check_query = "SELECT username, email FROM users WHERE username = ? OR email = ?"
            cursor.execute(check_query, (username, email))
            existing_user = cursor.fetchone()
            
            if existing_user:
                if existing_user[0] == username:
                    return False, "Username already exists"
                else:
                    return False, "Email already exists"
            
            # Hash password and insert user
            password_hash = self.db.hash_password(password)
            insert_query = "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)"
            cursor.execute(insert_query, (username, email, password_hash))
            self.db.connection.commit()
            
            return True, "User registered successfully"
            
        except sqlite3.Error as e:
            return False, f"Database error: {e}"
        finally:
            cursor.close()
    
    def login_user(self, username, password):
        """Authenticate user login"""
        try:
            cursor = self.db.connection.cursor()
            
            # Get user details
            query = "SELECT user_id, username, password_hash FROM users WHERE username = ?"
            cursor.execute(query, (username,))
            user = cursor.fetchone()
            
            if user and self.db.verify_password(password, user[2]):
                return True, {"user_id": user[0], "username": user[1]}, "Login successful"
            else:
                return False, None, "Invalid username or password"
                
        except sqlite3.Error as e:
            return False, None, f"Database error: {e}"
        finally:
            cursor.close()
    
    def get_user_by_id(self, user_id):
        """Get user information by ID"""
        try:
            cursor = self.db.connection.cursor()
            query = "SELECT user_id, username, email FROM users WHERE user_id = ?"
            cursor.execute(query, (user_id,))
            user = cursor.fetchone()
            
            if user:
                return {"user_id": user[0], "username": user[1], "email": user[2]}
            return None
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
        finally:
            cursor.close()

class StudySessionManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def log_study_session(self, user_id, subject, duration_minutes, mood, productivity, notes="", session_date=None):
        """Log a new study session"""
        try:
            cursor = self.db.connection.cursor()
            
            if session_date is None:
                session_date = date.today()
            
            insert_query = """
            INSERT INTO study_sessions (user_id, subject, duration_minutes, mood, productivity, notes, session_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (user_id, subject, duration_minutes, mood, productivity, notes, session_date))
            self.db.connection.commit()
            
            return True, "Study session logged successfully"
            
        except sqlite3.Error as e:
            return False, f"Database error: {e}"
        finally:
            cursor.close()
    
    def get_user_sessions(self, user_id, limit=None):
        """Get all study sessions for a user"""
        try:
            cursor = self.db.connection.cursor()
            
            if limit:
                query = """
                SELECT session_id, subject, duration_minutes, mood, productivity, notes, session_date, created_at
                FROM study_sessions 
                WHERE user_id = ? 
                ORDER BY session_date DESC, created_at DESC
                LIMIT ?
                """
                cursor.execute(query, (user_id, limit))
            else:
                query = """
                SELECT session_id, subject, duration_minutes, mood, productivity, notes, session_date, created_at
                FROM study_sessions 
                WHERE user_id = ? 
                ORDER BY session_date DESC, created_at DESC
                """
                cursor.execute(query, (user_id,))
            
            sessions = cursor.fetchall()
            return sessions
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
        finally:
            cursor.close()
    
    def get_total_study_time(self, user_id):
        """Get total study time for a user"""
        try:
            cursor = self.db.connection.cursor()
            query = "SELECT SUM(duration_minutes) FROM study_sessions WHERE user_id = ?"
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            
            return result[0] if result[0] else 0
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return 0
        finally:
            cursor.close()
    
    def get_subject_breakdown(self, user_id):
        """Get study time breakdown by subject"""
        try:
            cursor = self.db.connection.cursor()
            query = """
            SELECT subject, SUM(duration_minutes) as total_minutes, COUNT(*) as session_count
            FROM study_sessions 
            WHERE user_id = ? 
            GROUP BY subject
            ORDER BY total_minutes DESC
            """
            cursor.execute(query, (user_id,))
            subjects = cursor.fetchall()
            
            return subjects
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
        finally:
            cursor.close()
    
    def get_daily_study_data(self, user_id, days=30):
        """Get daily study data for charts"""
        try:
            cursor = self.db.connection.cursor()
            cutoff_date = date.today() - timedelta(days=days)
            
            query = """
            SELECT session_date, SUM(duration_minutes) as total_minutes
            FROM study_sessions 
            WHERE user_id = ? AND session_date >= ?
            GROUP BY session_date
            ORDER BY session_date
            """
            cursor.execute(query, (user_id, cutoff_date))
            
            data = cursor.fetchall()
            return data
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
        finally:
            cursor.close()

class GoalManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def set_weekly_goal(self, user_id, subject, weekly_target_minutes, week_start_date=None):
        """Set a weekly study goal for a subject"""
        try:
            cursor = self.db.connection.cursor()
            
            if week_start_date is None:
                today = date.today()
                # Get Monday of current week
                week_start_date = today - timedelta(days=today.weekday())
            
            # SQLite UPSERT syntax
            query = """
            INSERT INTO study_goals (user_id, subject, weekly_target_minutes, week_start_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, subject, week_start_date) 
            DO UPDATE SET weekly_target_minutes = excluded.weekly_target_minutes
            """
            cursor.execute(query, (user_id, subject, weekly_target_minutes, week_start_date))
            self.db.connection.commit()
            
            return True, "Weekly goal set successfully"
            
        except sqlite3.Error as e:
            return False, f"Database error: {e}"
        finally:
            cursor.close()
    
    def get_weekly_progress(self, user_id, week_start_date=None):
        """Get weekly progress for all subjects"""
        try:
            cursor = self.db.connection.cursor()
            
            if week_start_date is None:
                today = date.today()
                week_start_date = today - timedelta(days=today.weekday())
            
            week_end_date = week_start_date + timedelta(days=6)
            
            query = """
            SELECT 
                g.subject,
                g.weekly_target_minutes,
                COALESCE(SUM(s.duration_minutes), 0) as actual_minutes
            FROM study_goals g
            LEFT JOIN study_sessions s ON g.user_id = s.user_id 
                AND g.subject = s.subject 
                AND s.session_date BETWEEN ? AND ?
            WHERE g.user_id = ? AND g.week_start_date = ?
            GROUP BY g.subject, g.weekly_target_minutes
            """
            cursor.execute(query, (week_start_date, week_end_date, user_id, week_start_date))
            progress = cursor.fetchall()
            
            return progress
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
        finally:
            cursor.close()
    
    def get_user_goals(self, user_id):
        """Get all goals for a user"""
        try:
            cursor = self.db.connection.cursor()
            query = """
            SELECT goal_id, subject, weekly_target_minutes, week_start_date
            FROM study_goals 
            WHERE user_id = ?
            ORDER BY week_start_date DESC
            """
            cursor.execute(query, (user_id,))
            goals = cursor.fetchall()
            
            return goals
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
        finally:
            cursor.close()
