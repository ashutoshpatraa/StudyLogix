from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from database import initialize_database
from pomodoro_manager import PomodoroManager
import bcrypt
from datetime import datetime, date, timedelta
import os
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = 'studylogix-secret-key-change-this-in-production'

# Global database connection
db = None
pomodoro_manager = None

# Add thread safety for SQLite
import threading
db_lock = threading.Lock()

class WebUserManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def register_user(self, username, email, password):
        """Register a new user"""
        cursor = None
        with db_lock:  # Thread safety
            try:
                cursor = self.db.connection.cursor()
                
                # Check if username or email already exists
                cursor.execute("SELECT username, email FROM users WHERE username = ? OR email = ?", (username, email))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    if existing_user[0] == username:
                        return False, "Username already exists"
                    else:
                        return False, "Email already exists"
                
                # Hash password and insert user
                password_hash = self.db.hash_password(password)
                cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", 
                              (username, email, password_hash))
                self.db.connection.commit()
                
                return True, "User registered successfully"
                
            except Exception as e:
                return False, f"Database error: {e}"
            finally:
                if cursor:
                    cursor.close()
    
    def login_user(self, username, password):
        """Authenticate user login"""
        cursor = None
        with db_lock:  # Thread safety
            try:
                cursor = self.db.connection.cursor()
                
                cursor.execute("SELECT user_id, username, password_hash FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()
                
                if user and self.db.verify_password(password, user[2]):
                    return True, {"user_id": user[0], "username": user[1]}, "Login successful"
                else:
                    return False, None, "Invalid username or password"
                    
            except Exception as e:
                return False, None, f"Database error: {e}"
            finally:
                if cursor:
                    cursor.close()

class WebSessionManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def log_study_session(self, user_id, subject, duration_minutes, mood, productivity, notes="", session_date=None):
        """Log a new study session"""
        cursor = None
        with db_lock:  # Thread safety
            try:
                cursor = self.db.connection.cursor()
                
                if session_date is None:
                    session_date = date.today()
                
                cursor.execute("""
                    INSERT INTO study_sessions (user_id, subject, duration_minutes, mood, productivity, notes, session_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, subject, duration_minutes, mood, productivity, notes, session_date))
                self.db.connection.commit()
                
                return True, "Study session logged successfully"
                
            except Exception as e:
                return False, f"Database error: {e}"
            finally:
                if cursor:
                    cursor.close()
    
    def get_user_sessions(self, user_id, limit=None):
        """Get all study sessions for a user"""
        cursor = None
        with db_lock:  # Thread safety
            try:
                cursor = self.db.connection.cursor()
                
                if limit:
                    cursor.execute("""
                        SELECT session_id, subject, duration_minutes, mood, productivity, notes, session_date, created_at
                        FROM study_sessions 
                        WHERE user_id = ? 
                        ORDER BY session_date DESC, created_at DESC
                        LIMIT ?
                    """, (user_id, limit))
                else:
                    cursor.execute("""
                        SELECT session_id, subject, duration_minutes, mood, productivity, notes, session_date, created_at
                        FROM study_sessions 
                        WHERE user_id = ? 
                        ORDER BY session_date DESC, created_at DESC
                    """, (user_id,))
                
                sessions = cursor.fetchall()
                return sessions
                
            except Exception as e:
                print(f"Database error: {e}")
                return []
            finally:
                if cursor:
                    cursor.close()
    
    def get_total_study_time(self, user_id):
        """Get total study time for a user"""
        cursor = None
        with db_lock:  # Thread safety
            try:
                cursor = self.db.connection.cursor()
                cursor.execute("SELECT SUM(duration_minutes) FROM study_sessions WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                
                return result[0] if result[0] else 0
                
            except Exception as e:
                print(f"Database error: {e}")
                return 0
            finally:
                if cursor:
                    cursor.close()
    
    def get_subject_breakdown(self, user_id):
        """Get study time breakdown by subject"""
        cursor = None
        with db_lock:  # Thread safety
            try:
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    SELECT subject, SUM(duration_minutes) as total_minutes, COUNT(*) as session_count
                    FROM study_sessions 
                    WHERE user_id = ? 
                    GROUP BY subject
                    ORDER BY total_minutes DESC
                """, (user_id,))
                subjects = cursor.fetchall()
                
                return subjects
                
            except Exception as e:
                print(f"Database error: {e}")
                return []
            finally:
                if cursor:
                    cursor.close()
    
    def get_daily_study_data(self, user_id, days=30):
        """Get daily study data for charts"""
        cursor = None
        with db_lock:  # Thread safety
            try:
                cursor = self.db.connection.cursor()
                cutoff_date = date.today() - timedelta(days=days)
                
                cursor.execute("""
                    SELECT session_date, SUM(duration_minutes) as total_minutes
                    FROM study_sessions 
                    WHERE user_id = ? AND session_date >= ?
                    GROUP BY session_date
                    ORDER BY session_date
                """, (user_id, cutoff_date))
                
                data = cursor.fetchall()
                return data
                
            except Exception as e:
                print(f"Database error: {e}")
                return []
            finally:
                if cursor:
                    cursor.close()

# Initialize managers
def init_managers():
    global db, user_manager, session_manager, pomodoro_manager
    db = initialize_database()
    if db:
        user_manager = WebUserManager(db)
        session_manager = WebSessionManager(db)
        pomodoro_manager = PomodoroManager(db)
        
        # Create charts directory if it doesn't exist
        charts_dir = os.path.join('static', 'charts')
        if not os.path.exists(charts_dir):
            os.makedirs(charts_dir)
        
        return True
    return False

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register.html')
        
        success, message = user_manager.register_user(username, email, password)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        success, user_data, message = user_manager.login_user(username, password)
        
        if success:
            session['user_id'] = user_data['user_id']
            session['username'] = user_data['username']
            flash(message, 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get summary data including Pomodoro sessions
    study_time_data = pomodoro_manager.get_total_study_time_including_pomodoros(user_id)
    subjects_data = session_manager.get_subject_breakdown(user_id)
    recent_sessions = session_manager.get_user_sessions(user_id, 5)
    pomodoro_stats = pomodoro_manager.get_user_pomodoro_stats(user_id)
    
    # Debug: Print the study time data
    print(f"DEBUG - Study time data: {study_time_data}")
    print(f"DEBUG - Pomodoro stats: {pomodoro_stats}")
    
    # Use combined time from regular sessions and Pomodoros
    total_hours = study_time_data['total_hours']
    total_mins = study_time_data['remaining_minutes']
    
    return render_template('dashboard.html', 
                         total_hours=total_hours,
                         total_mins=total_mins,
                         pomodoro_stats=pomodoro_stats,
                         subjects_data=subjects_data,
                         recent_sessions=recent_sessions)

@app.route('/log_session', methods=['GET', 'POST'])
def log_session():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_id = session['user_id']
        subject = request.form['subject']
        duration = int(request.form['duration'])
        mood = request.form['mood']
        productivity = request.form['productivity']
        notes = request.form['notes']
        
        # Handle session date
        session_date_str = request.form.get('session_date')
        if session_date_str:
            session_date = datetime.strptime(session_date_str, '%Y-%m-%d').date()
        else:
            session_date = None
        
        success, message = session_manager.log_study_session(
            user_id, subject, duration, mood, productivity, notes, session_date
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'error')
    
    return render_template('log_session.html')

@app.route('/sessions')
def sessions():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    all_sessions = session_manager.get_user_sessions(user_id)
    
    return render_template('sessions.html', sessions=all_sessions)

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get analytics data
    total_time = session_manager.get_total_study_time(user_id)
    subjects_data = session_manager.get_subject_breakdown(user_id)
    daily_data = session_manager.get_daily_study_data(user_id, 30)
    
    return render_template('analytics.html',
                         total_time=total_time,
                         subjects_data=subjects_data,
                         daily_data=daily_data)

@app.route('/chart/<chart_type>')
def generate_chart(chart_type):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if chart_type == 'subject_pie':
        return generate_subject_pie_chart(user_id)
    elif chart_type == 'daily_timeline':
        return generate_daily_timeline_chart(user_id)
    
    return "Chart type not found", 404

def generate_subject_pie_chart(user_id):
    """Generate pie chart for subject distribution"""
    subjects_data = session_manager.get_subject_breakdown(user_id)
    
    if not subjects_data:
        return "No data available", 404
    
    subjects = [item[0] for item in subjects_data]
    minutes = [item[1] for item in subjects_data]
    hours = [m/60 for m in minutes]
    
    plt.figure(figsize=(10, 8))
    colors = plt.cm.Set3(np.linspace(0, 1, len(subjects)))
    
    wedges, texts, autotexts = plt.pie(hours, labels=subjects, autopct='%1.1f%%', 
                                      colors=colors, startangle=90)
    
    plt.title('Study Time Distribution by Subject', fontsize=16, fontweight='bold')
    plt.axis('equal')
    
    # Save to static directory
    chart_path = os.path.join('static', 'charts', f'subject_pie_{user_id}.png')
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return send_file(chart_path, mimetype='image/png')

def generate_daily_timeline_chart(user_id):
    """Generate daily timeline chart"""
    daily_data = session_manager.get_daily_study_data(user_id, 30)
    
    if not daily_data:
        return "No data available", 404
    
    dates = [item[0] for item in daily_data]
    minutes = [item[1] for item in daily_data]
    hours = [m/60 for m in minutes]
    
    plt.figure(figsize=(12, 6))
    plt.plot(dates, hours, marker='o', linewidth=2, markersize=6, color='#2E86AB')
    plt.fill_between(dates, hours, alpha=0.3, color='#2E86AB')
    
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Study Hours', fontsize=12)
    plt.title('Daily Study Time - Last 30 Days', fontsize=16, fontweight='bold')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Add average line
    if hours:
        avg_hours = sum(hours) / len(hours)
        plt.axhline(y=avg_hours, color='red', linestyle='--', alpha=0.7, 
                   label=f'Average: {avg_hours:.1f}h')
        plt.legend()
    
    plt.tight_layout()
    
    # Save to static directory
    chart_path = os.path.join('static', 'charts', f'daily_timeline_{user_id}.png')
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return send_file(chart_path, mimetype='image/png')

@app.route('/api/subjects')
def api_subjects():
    """API endpoint for subject data"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    subjects_data = session_manager.get_subject_breakdown(user_id)
    
    data = {
        'subjects': [item[0] for item in subjects_data],
        'hours': [item[1]/60 for item in subjects_data]
    }
    
    return jsonify(data)

# Pomodoro Timer Routes
@app.route('/pomodoro')
def pomodoro():
    """Display Pomodoro Timer page"""
    if 'user_id' not in session:
        flash('Please log in to access the Pomodoro timer', 'error')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    pomodoro_stats = pomodoro_manager.get_user_pomodoro_stats(user_id)
    recent_sessions = pomodoro_manager.get_recent_pomodoro_sessions(user_id, 5)
    
    return render_template('pomodoro.html', 
                         stats=pomodoro_stats, 
                         recent_sessions=recent_sessions)

@app.route('/api/pomodoro/start', methods=['POST'])
def start_pomodoro():
    """Start a new Pomodoro session"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    subject = data.get('subject', '').strip()
    
    if not subject:
        return jsonify({'error': 'Subject is required'}), 400
    
    success, session_id, message = pomodoro_manager.start_pomodoro_session(
        session['user_id'], subject
    )
    
    if success:
        return jsonify({
            'success': True, 
            'session_id': session_id, 
            'message': message
        })
    else:
        return jsonify({'error': message}), 500

@app.route('/api/pomodoro/complete', methods=['POST'])
def complete_pomodoro():
    """Complete a Pomodoro session"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    session_id = data.get('session_id')
    duration = data.get('duration', 25)
    
    print(f"DEBUG - Completing Pomodoro session {session_id} with duration {duration}")
    
    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400
    
    success, message = pomodoro_manager.complete_pomodoro_session(session_id, duration)
    
    print(f"DEBUG - Complete result: success={success}, message={message}")
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 500

@app.route('/api/pomodoro/cancel', methods=['POST'])
def cancel_pomodoro():
    """Cancel a Pomodoro session"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400
    
    success, message = pomodoro_manager.cancel_pomodoro_session(session_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 500

@app.route('/api/pomodoro/stats')
def pomodoro_stats():
    """Get Pomodoro statistics"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    stats = pomodoro_manager.get_user_pomodoro_stats(user_id)
    
    return jsonify(stats)

if __name__ == '__main__':
    if init_managers():
        print("🚀 Starting StudyLogix Web App...")
        print("📱 Open your browser and go to: http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("❌ Failed to initialize database!")
