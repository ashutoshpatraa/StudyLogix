"""
StudyLogix — Session Manager Service
Handles logging and retrieving regular study sessions and analytics.
"""

import logging
import threading
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class SessionManager:
    """Handles study session CRUD and analytics aggregation."""

    def __init__(self, db_manager):
        self.db = db_manager
        self.db_lock = threading.Lock()

    def log_study_session(self, user_id, subject, duration_minutes, mood, productivity, notes="", session_date=None):
        """Log a new study session."""
        with self.db_lock:
            cursor = None
            try:
                cursor = self.db.connection.cursor()
                if session_date is None:
                    session_date = date.today()
                cursor.execute("""
                    INSERT INTO study_sessions
                        (user_id, subject, duration_minutes, mood, productivity, notes, session_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, subject, duration_minutes, mood, productivity, notes, session_date))
                self.db.connection.commit()
                return True, "Study session logged successfully!"
            except Exception:
                logger.exception("Error logging study session")
                return False, "Failed to log session. Please try again."
            finally:
                if cursor:
                    cursor.close()

    def get_user_sessions(self, user_id, limit=None):
        """Retrieve study sessions for a user, most recent first."""
        with self.db_lock:
            cursor = None
            try:
                cursor = self.db.connection.cursor()
                query = """
                    SELECT session_id, subject, duration_minutes, mood,
                           productivity, notes, session_date, created_at
                    FROM study_sessions
                    WHERE user_id = ?
                    ORDER BY session_date DESC, created_at DESC
                """
                if limit:
                    query += " LIMIT ?"
                    cursor.execute(query, (user_id, limit))
                else:
                    cursor.execute(query, (user_id,))
                return cursor.fetchall()
            except Exception:
                logger.exception("Error fetching user sessions")
                return []
            finally:
                if cursor:
                    cursor.close()

    def get_total_study_time(self, user_id):
        """Return total study minutes for a user."""
        with self.db_lock:
            cursor = None
            try:
                cursor = self.db.connection.cursor()
                cursor.execute(
                    "SELECT SUM(duration_minutes) FROM study_sessions WHERE user_id = ?",
                    (user_id,),
                )
                result = cursor.fetchone()
                return result[0] if result[0] else 0
            except Exception:
                logger.exception("Error fetching total study time")
                return 0
            finally:
                if cursor:
                    cursor.close()

    def get_subject_breakdown(self, user_id):
        """Return study time grouped by subject."""
        with self.db_lock:
            cursor = None
            try:
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    SELECT subject, SUM(duration_minutes) AS total_minutes, COUNT(*) AS session_count
                    FROM study_sessions
                    WHERE user_id = ?
                    GROUP BY subject
                    ORDER BY total_minutes DESC
                """, (user_id,))
                return cursor.fetchall()
            except Exception:
                logger.exception("Error fetching subject breakdown")
                return []
            finally:
                if cursor:
                    cursor.close()

    def get_daily_study_data(self, user_id, days=30):
        """Return daily aggregated study data for charts."""
        with self.db_lock:
            cursor = None
            try:
                cursor = self.db.connection.cursor()
                cutoff_date = date.today() - timedelta(days=days)
                cursor.execute("""
                    SELECT session_date, SUM(duration_minutes) AS total_minutes
                    FROM study_sessions
                    WHERE user_id = ? AND session_date >= ?
                    GROUP BY session_date
                    ORDER BY session_date
                """, (user_id, cutoff_date))
                return cursor.fetchall()
            except Exception:
                logger.exception("Error fetching daily study data")
                return []
            finally:
                if cursor:
                    cursor.close()
