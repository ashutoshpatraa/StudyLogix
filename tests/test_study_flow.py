"""End-to-end smoke coverage for the core study loop."""

import app as flask_app
import pytest

from database import DatabaseManager


@pytest.fixture
def client():
    flask_app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    test_db = DatabaseManager(":memory:")
    assert test_db.connect() and test_db.create_tables()
    for manager in (
        flask_app.user_manager,
        flask_app.session_manager,
        flask_app.friend_manager,
        flask_app.pomodoro_manager,
    ):
        manager.db = test_db
    with flask_app.app.test_client() as test_client:
        test_client.post('/register', data={'username': 'learner', 'password': 'studytest1'})
        test_client.post('/login', data={'username': 'learner', 'password': 'studytest1'})
        yield test_client


def test_goal_log_timer_and_analytics_share_one_record(client):
    response = client.post('/daily-goal', data={
        'target_minutes': '75',
        'subject': 'Calculus',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'75m target' in response.data
    assert b'Continue Calculus' in response.data

    response = client.post('/log_session', data={
        'subject': 'Calculus',
        'duration': '30',
        'mood': 'good',
        'productivity': 'high',
        'notes': 'Limits practice',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'30m studied' in response.data

    started = client.post('/api/pomodoro/start', json={'subject': 'Physics'})
    assert started.status_code == 200
    session_id = started.get_json()['session_id']
    completed = client.post('/api/pomodoro/complete', json={
        'session_id': session_id,
        'duration': 25,
    })
    assert completed.status_code == 200

    dashboard = client.get('/dashboard')
    assert b'55m studied' in dashboard.data
    assert b'Physics' in dashboard.data
    assert client.get('/analytics').status_code == 200
    assert client.get('/sessions').status_code == 200
