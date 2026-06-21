"""
Authentication flow tests for StudyLogix.

Covers:
- Successful registration
- Login immediately after registration
- Session persistence after login
- Duplicate username rejection
- Invalid username (too short, bad chars)
- Invalid password (too short)
- Wrong password on login
- Unknown username on login
- Logout clears session
"""

import pytest
from app import app
from database import DatabaseManager


@pytest.fixture
def client():
    """Provide a Flask test client backed by an isolated in-memory DB."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    test_db = DatabaseManager(":memory:")
    test_db.connect()
    test_db.create_tables()

    with app.test_client() as test_client:
        import app as flask_app
        flask_app.db = test_db
        flask_app.user_manager.db = test_db
        flask_app.session_manager.db = test_db
        flask_app.friend_manager.db = test_db
        flask_app.pomodoro_manager.db = test_db
        yield test_client


# ---------------------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------------------

def test_register_success(client):
    """Valid credentials should create an account and redirect to login."""
    rv = client.post('/register', data={
        'username': 'newuser',
        'password': 'securepass123',
    }, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Account created successfully' in rv.data


def test_register_then_login(client):
    """User should be able to log in immediately after registering."""
    client.post('/register', data={
        'username': 'flowuser',
        'password': 'mypassword1',
    })
    rv = client.post('/login', data={
        'username': 'flowuser',
        'password': 'mypassword1',
    }, follow_redirects=True)
    assert rv.status_code == 200
    # Dashboard is shown after successful login
    assert b'flowuser' in rv.data or b'Quick Start' in rv.data


def test_session_persists_after_login(client):
    """After login, authenticated routes should be accessible."""
    client.post('/register', data={
        'username': 'sessuser',
        'password': 'passw0rd!',
    })
    client.post('/login', data={
        'username': 'sessuser',
        'password': 'passw0rd!',
    })
    # /dashboard requires login; if session is set it returns 200
    rv = client.get('/dashboard')
    assert rv.status_code == 200


def test_register_duplicate_username(client):
    """Registering with an existing username must return an error."""
    client.post('/register', data={
        'username': 'dupuser',
        'password': 'password123',
    })
    rv = client.post('/register', data={
        'username': 'dupuser',
        'password': 'password123',
    }, follow_redirects=True)
    assert b'already exists' in rv.data or b'error' in rv.data.lower()


def test_register_username_too_short(client):
    """Username shorter than 3 chars should be rejected."""
    rv = client.post('/register', data={
        'username': 'ab',
        'password': 'password123',
    }, follow_redirects=True)
    assert b'3-30 characters' in rv.data or b'Username' in rv.data


def test_register_invalid_username_chars(client):
    """Username with special characters should be rejected."""
    rv = client.post('/register', data={
        'username': 'bad user!',
        'password': 'password123',
    }, follow_redirects=True)
    assert b'3-30 characters' in rv.data or b'Username' in rv.data


def test_register_password_too_short(client):
    """Password shorter than 8 chars should be rejected."""
    rv = client.post('/register', data={
        'username': 'validuser',
        'password': 'short',
    }, follow_redirects=True)
    assert b'8 characters' in rv.data or b'Password' in rv.data


# ---------------------------------------------------------------------------
# Login Tests
# ---------------------------------------------------------------------------

def test_login_wrong_password(client):
    """Wrong password should return an error, not log the user in."""
    client.post('/register', data={
        'username': 'realuser',
        'password': 'correctpassword',
    })
    rv = client.post('/login', data={
        'username': 'realuser',
        'password': 'wrongpassword',
    }, follow_redirects=True)
    # Must not land on dashboard
    assert b'Quick Start' not in rv.data
    assert b'Invalid' in rv.data or b'error' in rv.data.lower()


def test_login_unknown_username(client):
    """Login with a non-existent username should fail gracefully."""
    rv = client.post('/login', data={
        'username': 'ghostuser',
        'password': 'password123',
    }, follow_redirects=True)
    assert b'Quick Start' not in rv.data
    assert b'Invalid' in rv.data or b'error' in rv.data.lower()


# ---------------------------------------------------------------------------
# Logout Tests
# ---------------------------------------------------------------------------

def test_logout_clears_session(client):
    """Logout should clear the session and redirect unauthenticated users."""
    client.post('/register', data={
        'username': 'logoutuser',
        'password': 'logoutpass1',
    })
    client.post('/login', data={
        'username': 'logoutuser',
        'password': 'logoutpass1',
    })
    # Confirm we're logged in
    rv = client.get('/dashboard')
    assert rv.status_code == 200

    # Now logout
    client.get('/logout', follow_redirects=True)

    # Dashboard must redirect after logout
    rv = client.get('/dashboard', follow_redirects=False)
    assert rv.status_code == 302
    assert 'login' in rv.headers['Location']
