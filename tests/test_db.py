import pytest
from database import DatabaseManager

def test_database_initialization():
    """Test that the database initializes and creates required tables."""
    db = DatabaseManager(":memory:")
    db.connect()
    success = db.create_tables()
    assert success is True
    
    cursor = db.connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert 'users' in tables
    assert 'study_sessions' in tables
    assert 'pomodoro_sessions' in tables
    assert 'friendships' in tables
