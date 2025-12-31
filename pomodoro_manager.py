"""
Pomodoro Timer Manager for StudyLogix
Handles Pomodoro session tracking and database operations
"""

import threading
from datetime import datetime, timedelta

class PomodoroManager:
    def __init__(self, db):
        self.db = db
        self.db_lock = threading.Lock()
    
    def start_pomodoro_session(self, user_id, subject):
        """Start a new Pomodoro session"""
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
                
            except Exception as e:
                print(f"Error starting Pomodoro session: {e}")
                return False, None, f"Failed to start session: {e}"
            finally:
                cursor.close()
    
    def complete_pomodoro_session(self, session_id, duration_minutes=25):
        """Complete a Pomodoro session"""
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
                else:
                    return False, "Session not found"
                    
            except Exception as e:
                print(f"Error completing Pomodoro session: {e}")
                return False, f"Failed to complete session: {e}"
            finally:
                cursor.close()
    
    def cancel_pomodoro_session(self, session_id):
        """Cancel an incomplete Pomodoro session"""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                cursor.execute("""
                    UPDATE pomodoro_sessions 
                    SET status = ?
                    WHERE session_id = ? AND status = ?
                """, ('cancelled', session_id, 'active'))
                
                self.db.connection.commit()
                
                return True, "Pomodoro session cancelled"
                    
            except Exception as e:
                print(f"Error cancelling Pomodoro session: {e}")
                return False, f"Failed to cancel session: {e}"
            finally:
                cursor.close()
    
    def get_user_pomodoro_stats(self, user_id):
        """Get Pomodoro statistics for a user"""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                # Get total completed Pomodoros
                cursor.execute("""
                    SELECT COUNT(*) as total_sessions, 
                           SUM(duration_minutes) as total_minutes,
                           COUNT(CASE WHEN DATE(started_at) = DATE('now') THEN 1 END) as today_sessions
                    FROM pomodoro_sessions 
                    WHERE user_id = ? AND status = ?
                """, (user_id, 'completed'))
                
                stats = cursor.fetchone()
                
                # Get subject breakdown
                cursor.execute("""
                    SELECT subject, COUNT(*) as sessions, SUM(duration_minutes) as minutes
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
                    'subjects': [(row[0], row[1], row[2]) for row in subjects]
                }
                
            except Exception as e:
                print(f"Error getting Pomodoro stats: {e}")
                return {
                    'total_sessions': 0,
                    'total_minutes': 0,
                    'today_sessions': 0,
                    'subjects': []
                }
            finally:
                cursor.close()
    
    def get_recent_pomodoro_sessions(self, user_id, limit=10):
        """Get recent Pomodoro sessions for a user"""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                cursor.execute("""
                    SELECT session_id, subject, started_at, completed_at, duration_minutes, status
                    FROM pomodoro_sessions 
                    WHERE user_id = ? AND status = ?
                    ORDER BY started_at DESC 
                    LIMIT ?
                """, (user_id, 'completed', limit))
                
                sessions = cursor.fetchall()
                return [(row[0], row[1], row[2], row[3], row[4], row[5]) for row in sessions]
                
            except Exception as e:
                print(f"Error getting recent Pomodoro sessions: {e}")
                return []
            finally:
                cursor.close()
    
    def get_total_study_time_including_pomodoros(self, user_id):
        """Get total study time including both regular sessions and Pomodoros"""
        with self.db_lock:
            cursor = self.db.connection.cursor()
            try:
                # Get regular study session time
                cursor.execute("""
                    SELECT COALESCE(SUM(duration_minutes), 0) as regular_time
                    FROM study_sessions 
                    WHERE user_id = ?
                """, (user_id,))
                
                regular_time = cursor.fetchone()[0] or 0
                
                # Get Pomodoro session time
                cursor.execute("""
                    SELECT COALESCE(SUM(duration_minutes), 0) as pomodoro_time
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
                    'remaining_minutes': total_time % 60
                }
                
            except Exception as e:
                print(f"Error calculating total study time: {e}")
                return {
                    'regular_minutes': 0,
                    'pomodoro_minutes': 0,
                    'total_minutes': 0,
                    'total_hours': 0,
                    'remaining_minutes': 0
                }
            finally:
                cursor.close()
