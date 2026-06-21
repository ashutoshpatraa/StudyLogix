import os
import pytest
from app import app
from database import DatabaseManager

@pytest.fixture
def client():
    # Setup in-memory DB for tests
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Overwrite DB path to memory
    test_db = DatabaseManager(":memory:")
    test_db.connect()
    test_db.create_tables()
    
    with app.test_client() as client:
        # Patch the global DB for tests
        import app as flask_app
        flask_app.db = test_db
        flask_app.user_manager.db = test_db
        flask_app.session_manager.db = test_db
        flask_app.friend_manager.db = test_db
        flask_app.pomodoro_manager.db = test_db
        yield client

def test_register_login(client):
    """Test user registration and subsequent login."""
    # Test registration
    rv = client.post('/register', data={
        'username': 'testuser',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert b'Account created successfully' in rv.data or b'Analytics Dashboard' in rv.data

    # Test login
    rv = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    assert b'System Authorized' in rv.data or b'Quick Start' in rv.data
