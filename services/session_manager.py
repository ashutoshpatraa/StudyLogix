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
        """Return total recorded minutes, including completed focus timers."""
        with self.db_lock:
            cursor = None
            try:
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    SELECT SUM(minutes) FROM (
                        SELECT duration_minutes AS minutes FROM study_sessions WHERE user_id = ?
                        UNION ALL
                        SELECT duration_minutes AS minutes FROM pomodoro_sessions
                        WHERE user_id = ? AND status = 'completed'
                    )
                """, (user_id, user_id))
                result = cursor.fetchone()
                return result[0] if result[0] else 0
            except Exception:
                logger.exception("Error fetching total study time")
                return 0
            finally:
                if cursor:
                    cursor.close()

    def get_subject_breakdown(self, user_id):
        """Return all recorded study time grouped by subject."""
        with self.db_lock:
            cursor = None
            try:
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    SELECT subject, SUM(minutes) AS total_minutes, COUNT(*) AS session_count
                    FROM (
                        SELECT subject, duration_minutes AS minutes
                        FROM study_sessions WHERE user_id = ?
                        UNION ALL
                        SELECT subject, duration_minutes AS minutes
                        FROM pomodoro_sessions WHERE user_id = ? AND status = 'completed'
                    )
                    GROUP BY subject
                    ORDER BY total_minutes DESC
                """, (user_id, user_id))
                return cursor.fetchall()
            except Exception:
                logger.exception("Error fetching subject breakdown")
                return []
            finally:
                if cursor:
                    cursor.close()

    def get_daily_study_data(self, user_id, days=30):
        """Return daily study data from logs and completed focus timers."""
        with self.db_lock:
            cursor = None
            try:
                cursor = self.db.connection.cursor()
                cutoff_date = date.today() - timedelta(days=days)
                cursor.execute("""
                    SELECT study_date, SUM(minutes) AS total_minutes
                    FROM (
                        SELECT session_date AS study_date, duration_minutes AS minutes
                        FROM study_sessions WHERE user_id = ? AND session_date >= ?
                        UNION ALL
                        SELECT DATE(started_at) AS study_date, duration_minutes AS minutes
                        FROM pomodoro_sessions
                        WHERE user_id = ? AND status = 'completed' AND DATE(started_at) >= ?
                    )
                    GROUP BY study_date
                    ORDER BY study_date
                """, (user_id, cutoff_date, user_id, cutoff_date))
                return cursor.fetchall()
            except Exception:
                logger.exception("Error fetching daily study data")
                return []
            finally:
                if cursor:
                    cursor.close()

    def get_recent_learning(self, user_id, limit=5):
        """Return one chronology spanning manual logs and focus timers."""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                cursor.execute("""
                    SELECT subject, minutes, study_date, source FROM (
                        SELECT subject, duration_minutes AS minutes,
                               session_date AS study_date, 'Manual log' AS source,
                               created_at AS sort_time
                        FROM study_sessions WHERE user_id = ?
                        UNION ALL
                        SELECT subject, duration_minutes AS minutes,
                               DATE(started_at) AS study_date, 'Focus timer' AS source,
                               started_at AS sort_time
                        FROM pomodoro_sessions WHERE user_id = ? AND status = 'completed'
                    )
                    ORDER BY study_date DESC, sort_time DESC
                    LIMIT ?
                """, (user_id, user_id, limit))
                return [
                    {'subject': row[0], 'minutes': row[1], 'date': row[2], 'source': row[3]}
                    for row in cursor.fetchall()
                ]
            except Exception:
                logger.exception("Error fetching recent learning")
                return []
            finally:
                cursor.close()

    def get_daily_goal(self, user_id, goal_date=None):
        """Return the user's explicit target for a date, or None."""
        goal_date = goal_date or date.today()
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                cursor.execute("""
                    SELECT target_minutes, subject
                    FROM daily_goals
                    WHERE user_id = ? AND goal_date = ?
                """, (user_id, goal_date))
                row = cursor.fetchone()
                return {'target_minutes': row[0], 'subject': row[1]} if row else None
            except Exception:
                logger.exception("Error fetching daily goal")
                return None
            finally:
                cursor.close()

    def set_daily_goal(self, user_id, target_minutes, subject=None, goal_date=None):
        """Create or revise the user's target for a date."""
        goal_date = goal_date or date.today()
        subject = subject.strip() if subject else None
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                cursor.execute("""
                    INSERT INTO daily_goals (user_id, goal_date, target_minutes, subject)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, goal_date) DO UPDATE SET
                        target_minutes = excluded.target_minutes,
                        subject = excluded.subject,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, goal_date, target_minutes, subject))
                self.db.connection.commit()
                return True
            except Exception:
                self.db.connection.rollback()
                logger.exception("Error saving daily goal")
                return False
            finally:
                cursor.close()
