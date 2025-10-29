import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_login_page_shows(client):
    rv = client.get('/login')
    assert b'Login' in rv.data

def test_login_success(client):
    rv = client.post('/login', data={'username': 'alice', 'password': 'password123'}, follow_redirects=True)
    assert b'Welcome' in rv.data

def test_login_failure(client):
    rv = client.post('/login', data={'username': 'alice', 'password': 'wrongpass'}, follow_redirects=True)
    assert b'Invalid username or password' in rv.data
