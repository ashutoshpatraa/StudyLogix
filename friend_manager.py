import sqlite3
from datetime import datetime

class FriendManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def send_friend_request(self, user_id, friend_username):
        """Send a friend request to another user"""
        cursor = self.db.connection.cursor()
        try:
            # Get friend's user_id from username
            cursor.execute("SELECT user_id FROM users WHERE username = ?", (friend_username,))
            result = cursor.fetchone()
            
            if not result:
                return False, "User not found"
            
            friend_id = result[0]
            
            if user_id == friend_id:
                return False, "Cannot add yourself as a friend"
            
            # Check if friendship already exists
            cursor.execute("""
                SELECT status FROM friendships 
                WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)
            """, (user_id, friend_id, friend_id, user_id))
            
            existing = cursor.fetchone()
            if existing:
                if existing[0] == 'accepted':
                    return False, "Already friends"
                elif existing[0] == 'pending':
                    return False, "Friend request already pending"
                elif existing[0] == 'blocked':
                    return False, "Cannot send friend request"
            
            # Send friend request
            cursor.execute("""
                INSERT INTO friendships (user_id, friend_id, status)
                VALUES (?, ?, 'pending')
            """, (user_id, friend_id))
            
            self.db.connection.commit()
            return True, "Friend request sent!"
            
        except sqlite3.Error as e:
            print(f"Error sending friend request: {e}")
            return False, "Failed to send friend request"
        finally:
            cursor.close()
    
    def respond_to_request(self, friendship_id, user_id, accept):
        """Accept or reject a friend request"""
        cursor = self.db.connection.cursor()
        try:
            # Verify this request is for the current user
            cursor.execute("""
                SELECT user_id, friend_id FROM friendships 
                WHERE friendship_id = ? AND friend_id = ? AND status = 'pending'
            """, (friendship_id, user_id))
            
            result = cursor.fetchone()
            if not result:
                return False, "Friend request not found"
            
            new_status = 'accepted' if accept else 'rejected'
            cursor.execute("""
                UPDATE friendships 
                SET status = ?, responded_at = CURRENT_TIMESTAMP
                WHERE friendship_id = ?
            """, (new_status, friendship_id))
            
            self.db.connection.commit()
            return True, f"Friend request {new_status}"
            
        except sqlite3.Error as e:
            print(f"Error responding to friend request: {e}")
            return False, "Failed to respond to request"
        finally:
            cursor.close()
    
    def get_pending_requests(self, user_id):
        """Get pending friend requests received by user"""
        cursor = self.db.connection.cursor()
        try:
            cursor.execute("""
                SELECT f.friendship_id, u.username, f.requested_at
                FROM friendships f
                JOIN users u ON f.user_id = u.user_id
                WHERE f.friend_id = ? AND f.status = 'pending'
                ORDER BY f.requested_at DESC
            """, (user_id,))
            
            requests = []
            for row in cursor.fetchall():
                requests.append({
                    'friendship_id': row[0],
                    'username': row[1],
                    'requested_at': row[2]
                })
            
            return requests
            
        except sqlite3.Error as e:
            print(f"Error getting pending requests: {e}")
            return []
        finally:
            cursor.close()
    
    def get_friends_list(self, user_id):
        """Get list of accepted friends"""
        cursor = self.db.connection.cursor()
        try:
            cursor.execute("""
                SELECT DISTINCT u.user_id, u.username, u.created_at
                FROM users u
                JOIN friendships f ON (
                    (f.user_id = ? AND f.friend_id = u.user_id) OR
                    (f.friend_id = ? AND f.user_id = u.user_id)
                )
                WHERE f.status = 'accepted'
                ORDER BY u.username
            """, (user_id, user_id))
            
            friends = []
            for row in cursor.fetchall():
                friends.append({
                    'user_id': row[0],
                    'username': row[1],
                    'member_since': row[2]
                })
            
            return friends
            
        except sqlite3.Error as e:
            print(f"Error getting friends list: {e}")
            return []
        finally:
            cursor.close()
    
    def remove_friend(self, user_id, friend_id):
        """Remove a friend"""
        cursor = self.db.connection.cursor()
        try:
            cursor.execute("""
                DELETE FROM friendships 
                WHERE ((user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?))
                AND status = 'accepted'
            """, (user_id, friend_id, friend_id, user_id))
            
            self.db.connection.commit()
            return True, "Friend removed"
            
        except sqlite3.Error as e:
            print(f"Error removing friend: {e}")
            return False, "Failed to remove friend"
        finally:
            cursor.close()
    
    def get_friends_progress(self, user_id):
        """Get study progress of all friends"""
        cursor = self.db.connection.cursor()
        try:
            cursor.execute("""
                SELECT DISTINCT u.user_id, u.username
                FROM users u
                JOIN friendships f ON (
                    (f.user_id = ? AND f.friend_id = u.user_id) OR
                    (f.friend_id = ? AND f.user_id = u.user_id)
                )
                WHERE f.status = 'accepted'
            """, (user_id, user_id))
            
            friends_progress = []
            for row in cursor.fetchall():
                friend_user_id = row[0]
                friend_username = row[1]
                
                # Get total study time (regular sessions)
                cursor.execute("""
                    SELECT COALESCE(SUM(duration_minutes), 0)
                    FROM study_sessions
                    WHERE user_id = ? AND session_date >= date('now', '-7 days')
                """, (friend_user_id,))
                regular_mins = cursor.fetchone()[0]
                
                # Get pomodoro time
                cursor.execute("""
                    SELECT COALESCE(SUM(duration_minutes), 0)
                    FROM pomodoro_sessions
                    WHERE user_id = ? AND status = 'completed' 
                    AND DATE(started_at) >= date('now', '-7 days')
                """, (friend_user_id,))
                pomodoro_mins = cursor.fetchone()[0]
                
                # Get today's sessions
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM pomodoro_sessions
                    WHERE user_id = ? AND status = 'completed' 
                    AND DATE(started_at) = date('now')
                """, (friend_user_id,))
                today_sessions = cursor.fetchone()[0]
                
                friends_progress.append({
                    'user_id': friend_user_id,
                    'username': friend_username,
                    'weekly_minutes': regular_mins + pomodoro_mins,
                    'today_sessions': today_sessions
                })
            
            return friends_progress
            
        except sqlite3.Error as e:
            print(f"Error getting friends progress: {e}")
            return []
        finally:
            cursor.close()
    
    def get_active_friend_timers(self, user_id):
        """Get currently active timers for all friends"""
        cursor = self.db.connection.cursor()
        try:
            cursor.execute("""
                SELECT DISTINCT u.username, t.subject, t.duration_minutes, 
                       t.time_remaining, t.is_break, t.last_updated
                FROM active_timers t
                JOIN users u ON t.user_id = u.user_id
                JOIN friendships f ON (
                    (f.user_id = ? AND f.friend_id = t.user_id) OR
                    (f.friend_id = ? AND f.user_id = t.user_id)
                )
                WHERE f.status = 'accepted'
                AND t.time_remaining > 0
                ORDER BY u.username
            """, (user_id, user_id))
            
            active_timers = []
            for row in cursor.fetchall():
                active_timers.append({
                    'username': row[0],
                    'subject': row[1],
                    'duration_minutes': row[2],
                    'time_remaining': row[3],
                    'is_break': bool(row[4]),
                    'last_updated': row[5]
                })
            
            return active_timers
            
        except sqlite3.Error as e:
            print(f"Error getting active timers: {e}")
            return []
        finally:
            cursor.close()
    
    def update_active_timer(self, user_id, session_id, subject, duration_minutes, time_remaining, is_break):
        """Update or insert active timer for a user"""
        cursor = self.db.connection.cursor()
        try:
            # Delete old timer for this user
            cursor.execute("DELETE FROM active_timers WHERE user_id = ?", (user_id,))
            
            # Insert new timer if time remaining
            if time_remaining > 0:
                cursor.execute("""
                    INSERT INTO active_timers 
                    (user_id, session_id, subject, duration_minutes, time_remaining, is_break, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, session_id, subject, duration_minutes, time_remaining, int(is_break)))
            
            self.db.connection.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Error updating active timer: {e}")
            return False
        finally:
            cursor.close()
    
    def clear_active_timer(self, user_id):
        """Clear active timer for a user"""
        cursor = self.db.connection.cursor()
        try:
            cursor.execute("DELETE FROM active_timers WHERE user_id = ?", (user_id,))
            self.db.connection.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Error clearing active timer: {e}")
            return False
        finally:
            cursor.close()
