"""Shared setup for the tests.

Each test gets its own app with its own temporary database, filled with the
sample data. Nothing touches the real database in the instance folder.
"""

import re

import pytest

from profpulse import create_app
from profpulse.db import get_db, init_db
from profpulse.seed import seed

PASSWORD = "correct-horse-battery"


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-key",
        "DATABASE": str(tmp_path / "test.sqlite"),
        "SHOW_VERIFY_LINK": True,
    })
    with app.app_context():
        init_db()
        seed()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(client, path="/login"):
    """Loads a page and returns the CSRF token from its form."""
    page = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)


def post(client, path, data=None, token_from="/login", **kwargs):
    """POSTs a form with a valid CSRF token added."""
    data = dict(data or {})
    data["csrf_token"] = csrf(client, token_from)
    return client.post(path, data=data, **kwargs)


def register(client, email="student@uoguelph.ca", password=PASSWORD):
    return post(client, "/register", {"email": email, "password": password, "confirm": password})


def verify_link(client):
    """Returns the path of the verification link shown on the page after sign-up."""
    page = client.get("/verify-sent").get_data(as_text=True)
    return re.search(r'href="http://localhost(/verify/[^"]+)"', page).group(1)


def login(client, email="student@uoguelph.ca", password=PASSWORD):
    return post(client, "/login", {"email": email, "password": password})


def make_verified_user(client, email="student@uoguelph.ca"):
    """Signs up, opens the verification link and logs in."""
    register(client, email)
    client.get(verify_link(client))
    return login(client, email)


def review_form(course_id, **changes):
    """A valid review. Pass keyword arguments to change single fields."""
    data = {
        "course_id": course_id, "term": "F26",
        "clarity": 5, "helpfulness": 4, "fairness": 3, "engagement": 4, "organization": 4,
        "tags": ["clear lectures", "fair exams"],
        "body": "Explains things clearly and the assignments match the lectures closely.",
    }
    data.update(changes)
    return data


def first_course_id(app, professor_id=1):
    with app.app_context():
        return get_db().execute(
            "SELECT course_id FROM teaches WHERE professor_id = ? ORDER BY course_id", (professor_id,)
        ).fetchone()[0]
