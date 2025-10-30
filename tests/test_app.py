import pytest
from app import app
import os

@pytest.fixture
def client():
    """Provide a Flask test client for the app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_login_page_shows(client):
    """✅ Basic check that the login page renders correctly."""
    rv = client.get('/login')
    assert b'Login' in rv.data


def test_login_success(client):
    """✅ Valid login should redirect to the dashboard or welcome page."""
    rv = client.post(
        '/login',
        data={'username': 'alice', 'password': 'password123'},
        follow_redirects=True
    )
    assert b'Welcome' in rv.data


def test_login_failure(client):
    """✅ Invalid login should show an error message."""
    rv = client.post(
        '/login',
        data={'username': 'alice', 'password': 'wrongpass'},
        follow_redirects=True
    )
    assert b'Invalid username or password' in rv.data


def test_force_failure_for_notification():
    """
    ❌ This test is intentionally designed to fail.
    Purpose: To verify Jenkins, Confluence, and email report behavior on failure.
    Set environment variable FORCE_FAIL=false to skip this failure.
    """
    # Allow toggling from Jenkins or local runs
    force_fail = os.getenv("FORCE_FAIL", "true").lower() == "true"

    if force_fail:
        # Intentional failure to test report pipeline
        assert False, "Intentional failure for CI/CD test result notification"
    else:
        assert True
