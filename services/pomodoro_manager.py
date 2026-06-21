"""
StudyLogix — Pomodoro Timer Manager
Handles Pomodoro session tracking, statistics, and database operations.
"""

import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


class PomodoroManager:
    """Manages Pomodoro timer sessions with thread-safe database access."""

    def __init__(self, db):
        self.db = db
        self.db_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Ownership verification (IDOR protection)
    # ------------------------------------------------------------------

    def verify_session_ownership(self, session_id, user_id):
        """Check that a pomodoro session belongs to the given user."""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                cursor.execute(
                    "SELECT 1 FROM pomodoro_sessions WHERE session_id = ? AND user_id = ?",
                    (session_id, user_id),
                )
                return cursor.fetchone() is not None
            except Exception:
                logger.exception("Error verifying session ownership")
                return False
            finally:
                cursor.close()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_pomodoro_session(self, user_id, subject):
        """Start a new Pomodoro session. Returns (success, session_id, message)."""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                cursor.execute("""
                    INSERT INTO pomodoro_sessions (user_id, subject, duration_minutes, status)
                    VALUES (?, ?, ?, ?)
                """, (user_id, subject, 25, 'active'))

                self.db.connection.commit()
                session_id = cursor.lastrowid
                return True, session_id, "Pomodoro session started!"
            except Exception:
                logger.exception("Error starting Pomodoro session")
                return False, None, "Failed to start session. Please try again."
            finally:
                cursor.close()

    def complete_pomodoro_session(self, session_id, duration_minutes=25):
        """Mark a Pomodoro session as completed. Returns (success, message)."""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                end_time = datetime.now()
                cursor.execute("""
                    UPDATE pomodoro_sessions
                    SET completed_at = ?, duration_minutes = ?, status = ?
                    WHERE session_id = ?
                """, (end_time, duration_minutes, 'completed', session_id))

                self.db.connection.commit()
                if cursor.rowcount > 0:
                    return True, "Pomodoro session completed!"
                return False, "Session not found."
            except Exception:
                logger.exception("Error completing Pomodoro session")
                return False, "Failed to complete session. Please try again."
            finally:
                cursor.close()

    def cancel_pomodoro_session(self, session_id):
        """Cancel an active Pomodoro session. Returns (success, message)."""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                cursor.execute("""
                    UPDATE pomodoro_sessions
                    SET status = ?
                    WHERE session_id = ? AND status = ?
                """, ('cancelled', session_id, 'active'))

                self.db.connection.commit()
                return True, "Pomodoro session cancelled."
            except Exception:
                logger.exception("Error cancelling Pomodoro session")
                return False, "Failed to cancel session. Please try again."
            finally:
                cursor.close()

    # ------------------------------------------------------------------
    # Statistics & history
    # ------------------------------------------------------------------

    def get_user_pomodoro_stats(self, user_id):
        """Return aggregated Pomodoro statistics for a user."""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                cursor.execute("""
                    SELECT COUNT(*) AS total_sessions,
                           COALESCE(SUM(duration_minutes), 0) AS total_minutes,
                           COUNT(CASE WHEN DATE(started_at) = DATE('now') THEN 1 END) AS today_sessions
                    FROM pomodoro_sessions
                    WHERE user_id = ? AND status = ?
                """, (user_id, 'completed'))
                stats = cursor.fetchone()

                cursor.execute("""
                    SELECT subject, COUNT(*) AS sessions, SUM(duration_minutes) AS minutes
                    FROM pomodoro_sessions
                    WHERE user_id = ? AND status = ?
                    GROUP BY subject
                    ORDER BY minutes DESC
                """, (user_id, 'completed'))
                subjects = cursor.fetchall()

                return {
                    'total_sessions': stats[0] or 0,
                    'total_minutes': stats[1] or 0,
                    'today_sessions': stats[2] or 0,
                    'subjects': [(row[0], row[1], row[2]) for row in subjects],
                }
            except Exception:
                logger.exception("Error fetching Pomodoro stats")
                return {
                    'total_sessions': 0,
                    'total_minutes': 0,
                    'today_sessions': 0,
                    'subjects': [],
                }
            finally:
                cursor.close()

    def get_recent_pomodoro_sessions(self, user_id, limit=10):
        """Return the most recent completed Pomodoro sessions."""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                cursor.execute("""
                    SELECT session_id, subject, started_at, completed_at,
                           duration_minutes, status
                    FROM pomodoro_sessions
                    WHERE user_id = ? AND status = ?
                    ORDER BY started_at DESC
                    LIMIT ?
                """, (user_id, 'completed', limit))
                return [
                    (row[0], row[1], row[2], row[3], row[4], row[5])
                    for row in cursor.fetchall()
                ]
            except Exception:
                logger.exception("Error fetching recent Pomodoro sessions")
                return []
            finally:
                cursor.close()

    def get_total_study_time_including_pomodoros(self, user_id):
        """Return combined study time from regular sessions and Pomodoros."""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                cursor.execute("""
                    SELECT COALESCE(SUM(duration_minutes), 0)
                    FROM study_sessions WHERE user_id = ?
                """, (user_id,))
                regular_time = cursor.fetchone()[0] or 0

                cursor.execute("""
                    SELECT COALESCE(SUM(duration_minutes), 0)
                    FROM pomodoro_sessions
                    WHERE user_id = ? AND status = ?
                """, (user_id, 'completed'))
                pomodoro_time = cursor.fetchone()[0] or 0

                total_time = regular_time + pomodoro_time
                return {
                    'regular_minutes': regular_time,
                    'pomodoro_minutes': pomodoro_time,
                    'total_minutes': total_time,
                    'total_hours': total_time // 60,
                    'remaining_minutes': total_time % 60,
                }
            except Exception:
                logger.exception("Error calculating total study time")
                return {
                    'regular_minutes': 0,
                    'pomodoro_minutes': 0,
                    'total_minutes': 0,
                    'total_hours': 0,
                    'remaining_minutes': 0,
                }
            finally:
                cursor.close()
