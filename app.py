"""
StudyLogix — Flask Web Application
A study session tracker with Pomodoro timer, analytics, and social features.
"""

import logging
import os
import re
import threading
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (
    Flask, flash, jsonify, redirect, render_template, request,
    session, url_for,
)
from flask_wtf.csrf import CSRFProtect

from database import initialize_database
from services.user_manager import UserManager
from services.session_manager import SessionManager
from services.friend_manager import FriendManager
from services.pomodoro_manager import PomodoroManager

# ---------------------------------------------------------------------------
# Application factory & configuration
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Security: read secret key from environment; fall back to random bytes in dev
_secret = os.environ.get('SECRET_KEY')
if _secret:
    app.secret_key = _secret
else:
    app.secret_key = os.urandom(32)
    app.logger.warning(
        "SECRET_KEY not set — using random bytes. "
        "Sessions will not persist across restarts. "
        "Set SECRET_KEY in your environment for production."
    )

# Session security configuration
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
)

# In production, enforce secure cookies
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True

# Initialize CSRF Protection
csrf = CSRFProtect(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security middleware — HTTP response headers
# ---------------------------------------------------------------------------

@app.after_request
def set_security_headers(response):
    """Inject security-related HTTP headers on every response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    # CSP: allow inline styles/scripts for the current design; tighten later
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    return response

# ---------------------------------------------------------------------------
# Custom Jinja2 filters
# ---------------------------------------------------------------------------

@app.template_filter('zfill')
def zfill_filter(value, width):
    """Pad a value with leading zeros."""
    return str(value).zfill(width)

# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,30}$')


def _validate_username(username: str) -> str | None:
    """Return an error message if username is invalid, else None."""
    if not username or not _USERNAME_RE.match(username):
        return "Username must be 3-30 characters (letters, numbers, underscores)."
    return None


def _validate_password(password: str) -> str | None:
    """Return an error message if password is too weak, else None."""
    if not password or len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def _validate_subject(subject: str) -> str | None:
    if not subject or len(subject.strip()) == 0:
        return "Subject is required."
    if len(subject) > 100:
        return "Subject must be 100 characters or fewer."
    return None


def _validate_duration(raw_value: str) -> tuple[int | None, str | None]:
    """Parse and validate duration. Returns (value, error)."""
    try:
        val = int(raw_value)
    except (ValueError, TypeError):
        return None, "Duration must be a number."
    if val < 1 or val > 600:
        return None, "Duration must be between 1 and 600 minutes."
    return val, None


def _validate_notes(notes: str) -> str | None:
    if notes and len(notes) > 1000:
        return "Notes must be 1000 characters or fewer."
    return None

# ---------------------------------------------------------------------------
# Authentication decorator
# ---------------------------------------------------------------------------

def login_required(f):
    """Decorator that redirects unauthenticated users to the login page."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def api_login_required(f):
    """Decorator for JSON API endpoints — returns 401 instead of redirect."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------------------------------------------------------
# Database & manager initialisation
# ---------------------------------------------------------------------------

# Global manager instances
db = None
user_manager = None
session_manager = None
pomodoro_manager = None
friend_manager = None


def init_managers():
    """Initialise database and all manager instances."""
    global db, user_manager, session_manager, pomodoro_manager, friend_manager
    db = initialize_database()
    if db:
        user_manager = UserManager(db)
        session_manager = SessionManager(db)
        pomodoro_manager = PomodoroManager(db)
        friend_manager = FriendManager(db)
        return True
    return False

# ---------------------------------------------------------------------------
# Routes — Public
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Validation
        err = _validate_username(username)
        if err:
            flash(err, 'error')
            return render_template('register.html')

        err = _validate_password(password)
        if err:
            flash(err, 'error')
            return render_template('register.html')

        success, message = user_manager.register_user(username, password)
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        success, user_data, message = user_manager.login_user(username, password)
        if success:
            session['user_id'] = user_data['user_id']
            session['username'] = user_data['username']
            session.permanent = True
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

# ---------------------------------------------------------------------------
# Routes — Authenticated pages
# ---------------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']

    study_time_data = pomodoro_manager.get_total_study_time_including_pomodoros(user_id)
    subjects_data = session_manager.get_subject_breakdown(user_id)
    recent_sessions = session_manager.get_user_sessions(user_id, 5)
    pomodoro_stats = pomodoro_manager.get_user_pomodoro_stats(user_id)
    heatmap_data = session_manager.get_daily_study_data(user_id, 365)

    # Compute today's minutes for the radial arc
    today_str = date.today().isoformat()
    today_minutes = sum(row[1] for row in heatmap_data if str(row[0]) == today_str)

    total_hours = study_time_data['total_hours']
    total_mins = study_time_data['remaining_minutes']

    return render_template(
        'dashboard.html',
        now=datetime.now(),
        total_hours=total_hours,
        total_mins=total_mins,
        pomodoro_stats=pomodoro_stats,
        subjects_data=subjects_data,
        recent_sessions=recent_sessions,
        heatmap_data=heatmap_data,
        today_minutes=today_minutes,
    )


@app.route('/log_session', methods=['GET', 'POST'])
@login_required
def log_session():
    if request.method == 'POST':
        user_id = session['user_id']
        subject = request.form.get('subject', '').strip()
        raw_duration = request.form.get('duration', '')
        mood = request.form.get('mood', '')
        productivity = request.form.get('productivity', '')
        notes = request.form.get('notes', '').strip()

        # Validate inputs
        err = _validate_subject(subject)
        if err:
            flash(err, 'error')
            return render_template('log_session.html')

        duration, err = _validate_duration(raw_duration)
        if err:
            flash(err, 'error')
            return render_template('log_session.html')

        err = _validate_notes(notes)
        if err:
            flash(err, 'error')
            return render_template('log_session.html')

        # Validate mood and productivity against allowed values
        allowed_moods = {'excellent', 'good', 'fair', 'poor'}
        allowed_productivity = {'very_high', 'high', 'medium', 'low', 'very_low'}
        if mood not in allowed_moods:
            flash('Invalid mood selection.', 'error')
            return render_template('log_session.html')
        if productivity not in allowed_productivity:
            flash('Invalid productivity selection.', 'error')
            return render_template('log_session.html')

        # Handle session date
        session_date_str = request.form.get('session_date')
        session_date = None
        if session_date_str:
            try:
                session_date = datetime.strptime(session_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'error')
                return render_template('log_session.html')

        success, message = session_manager.log_study_session(
            user_id, subject, duration, mood, productivity, notes, session_date,
        )
        if success:
            flash(message, 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'error')

    return render_template('log_session.html')


@app.route('/sessions')
@login_required
def sessions():
    user_id = session['user_id']
    all_sessions = session_manager.get_user_sessions(user_id)
    return render_template('sessions.html', sessions=all_sessions)


@app.route('/analytics')
@login_required
def analytics():
    user_id = session['user_id']
    total_time = session_manager.get_total_study_time(user_id)
    subjects_data = session_manager.get_subject_breakdown(user_id)
    daily_data = session_manager.get_daily_study_data(user_id, 30)
    return render_template(
        'analytics.html',
        total_time=total_time,
        subjects_data=subjects_data,
        daily_data=daily_data,
    )

# ---------------------------------------------------------------------------
# API — Analytics
# ---------------------------------------------------------------------------

@app.route('/api/analytics/subject_distribution')
@api_login_required
def api_subject_distribution():
    """Return subject distribution data as JSON for Chart.js."""
    user_id = session['user_id']
    subjects_data = session_manager.get_subject_breakdown(user_id)
    if not subjects_data:
        return jsonify({'success': False, 'error': 'No data available'}), 404

    subjects = [item[0] for item in subjects_data]
    hours = [item[1] / 60 for item in subjects_data]
    return jsonify({
        'success': True,
        'data': {
            'labels': subjects,
            'values': hours
        }
    })


@app.route('/api/analytics/daily_timeline')
@api_login_required
def api_daily_timeline():
    """Return daily timeline data as JSON for Chart.js."""
    user_id = session['user_id']
    days = request.args.get('days', 30, type=int)
    daily_data = session_manager.get_daily_study_data(user_id, days)
    if not daily_data:
        return jsonify({'success': False, 'error': 'No data available'}), 404

    dates = [item[0] for item in daily_data]
    hours = [item[1] / 60 for item in daily_data]
    return jsonify({
        'success': True,
        'data': {
            'labels': dates,
            'values': hours
        }
    })

# ---------------------------------------------------------------------------
# API — Subject data
# ---------------------------------------------------------------------------

@app.route('/api/subjects')
@api_login_required
def api_subjects():
    """Return subject breakdown as JSON."""
    user_id = session['user_id']
    subjects_data = session_manager.get_subject_breakdown(user_id)
    return jsonify({
        'subjects': [item[0] for item in subjects_data],
        'hours': [item[1] / 60 for item in subjects_data],
    })

# ---------------------------------------------------------------------------
# Routes — Pomodoro Timer
# ---------------------------------------------------------------------------

@app.route('/pomodoro')
@login_required
def pomodoro():
    """Display Pomodoro Timer page."""
    user_id = session['user_id']
    pomo_stats = pomodoro_manager.get_user_pomodoro_stats(user_id)
    recent_sessions = pomodoro_manager.get_recent_pomodoro_sessions(user_id, 5)
    return render_template(
        'pomodoro.html',
        pomodoro_stats=pomo_stats,
        recent_sessions=recent_sessions,
    )


@app.route('/api/pomodoro/start', methods=['POST'])
@api_login_required
def start_pomodoro():
    """Start a new Pomodoro session."""
    data = request.get_json(silent=True) or {}
    subject = data.get('subject', '').strip()

    err = _validate_subject(subject)
    if err:
        return jsonify({'error': err}), 400

    success, session_id, message = pomodoro_manager.start_pomodoro_session(
        session['user_id'], subject,
    )
    if success:
        return jsonify({'success': True, 'session_id': session_id, 'message': message})
    return jsonify({'error': message}), 500


@app.route('/api/pomodoro/complete', methods=['POST'])
@api_login_required
def complete_pomodoro():
    """Complete a Pomodoro session (with ownership verification)."""
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    duration = data.get('duration', 25)

    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400

    # IDOR protection: verify the session belongs to this user
    if not pomodoro_manager.verify_session_ownership(session_id, session['user_id']):
        return jsonify({'error': 'Session not found'}), 404

    success, message = pomodoro_manager.complete_pomodoro_session(session_id, duration)
    if success:
        return jsonify({'success': True, 'message': message})
    return jsonify({'error': message}), 500


@app.route('/api/pomodoro/cancel', methods=['POST'])
@api_login_required
def cancel_pomodoro():
    """Cancel a Pomodoro session (with ownership verification)."""
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'error': 'Session ID is required'}), 400

    # IDOR protection
    if not pomodoro_manager.verify_session_ownership(session_id, session['user_id']):
        return jsonify({'error': 'Session not found'}), 404

    success, message = pomodoro_manager.cancel_pomodoro_session(session_id)
    if success:
        return jsonify({'success': True, 'message': message})
    return jsonify({'error': message}), 500


@app.route('/api/pomodoro/stats')
@api_login_required
def pomodoro_stats():
    """Return Pomodoro statistics as JSON."""
    user_id = session['user_id']
    stats = pomodoro_manager.get_user_pomodoro_stats(user_id)
    return jsonify(stats)

# ---------------------------------------------------------------------------
# Routes — Friend Management
# ---------------------------------------------------------------------------

@app.route('/friends')
@login_required
def friends():
    """Display friends page."""
    user_id = session['user_id']
    friends_list = friend_manager.get_friends_list(user_id)
    pending_requests = friend_manager.get_pending_requests(user_id)
    friends_progress = friend_manager.get_friends_progress(user_id)
    active_timers = friend_manager.get_active_friend_timers(user_id)
    return render_template(
        'friends.html',
        friends=friends_list,
        pending_requests=pending_requests,
        friends_progress=friends_progress,
        active_timers=active_timers,
    )


@app.route('/api/friends/send_request', methods=['POST'])
@api_login_required
def send_friend_request():
    """Send a friend request."""
    data = request.get_json(silent=True) or {}
    friend_username = data.get('username', '').strip()

    if not friend_username:
        return jsonify({'error': 'Username is required'}), 400

    user_id = session['user_id']
    success, message = friend_manager.send_friend_request(user_id, friend_username)
    if success:
        return jsonify({'success': True, 'message': message})
    return jsonify({'error': message}), 400


@app.route('/api/friends/respond', methods=['POST'])
@api_login_required
def respond_friend_request():
    """Accept or reject a friend request."""
    data = request.get_json(silent=True) or {}
    friendship_id = data.get('friendship_id')
    accept = data.get('accept', False)

    if not friendship_id:
        return jsonify({'error': 'Friendship ID is required'}), 400

    user_id = session['user_id']
    success, message = friend_manager.respond_to_request(friendship_id, user_id, accept)
    if success:
        return jsonify({'success': True, 'message': message})
    return jsonify({'error': message}), 400


@app.route('/api/friends/remove', methods=['POST'])
@api_login_required
def remove_friend():
    """Remove a friend."""
    data = request.get_json(silent=True) or {}
    friend_id = data.get('friend_id')

    if not friend_id:
        return jsonify({'error': 'Friend ID is required'}), 400

    user_id = session['user_id']
    success, message = friend_manager.remove_friend(user_id, friend_id)
    if success:
        return jsonify({'success': True, 'message': message})
    return jsonify({'error': message}), 400


@app.route('/api/friends/active_timers')
@api_login_required
def get_active_timers():
    """Return active timers for all friends as JSON."""
    user_id = session['user_id']
    active_timers = friend_manager.get_active_friend_timers(user_id)
    return jsonify({'timers': active_timers})


@app.route('/api/timer/update', methods=['POST'])
@api_login_required
def update_timer():
    """Update active timer status for friend visibility."""
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    subject = data.get('subject')
    duration_minutes = data.get('duration_minutes')
    time_remaining = data.get('time_remaining')
    is_break = data.get('is_break', False)

    user_id = session['user_id']
    success = friend_manager.update_active_timer(
        user_id, session_id, subject, duration_minutes, time_remaining, is_break,
    )
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to update timer'}), 500

# ---------------------------------------------------------------------------
# Application startup
# ---------------------------------------------------------------------------

# Initialise managers at module load time (needed for gunicorn)
init_managers()

if __name__ == '__main__':
    if user_manager:
        logger.info("🚀 Starting StudyLogix Web App...")
        logger.info("📱 Open your browser and go to: http://localhost:5000")
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_ENV') != 'production'
        app.run(debug=debug, host='0.0.0.0', port=port)
    else:
        logger.error("❌ Failed to initialize database!")
