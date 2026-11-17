"""Accounts: sign-up rules, email verification, login and its limits."""

from conftest import PASSWORD, csrf, login, post, register, verify_link

from profpulse.db import get_db


def user_row(app, email="student@uoguelph.ca"):
    with app.app_context():
        return get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def test_other_email_domains_are_refused(app, client):
    response = register(client, "someone@gmail.com")
    assert "Use your @uoguelph.ca email address" in response.get_data(as_text=True)
    assert user_row(app, "someone@gmail.com") is None


def test_lookalike_domain_is_refused(app, client):
    """The address must END in the school domain, not just contain it."""
    register(client, "someone@uoguelph.ca.evil.com")
    assert user_row(app, "someone@uoguelph.ca.evil.com") is None


def test_short_password_is_refused(app, client):
    register(client, password="short")
    assert user_row(app) is None


def test_password_is_stored_as_a_hash(app, client):
    register(client)
    row = user_row(app)
    assert row["password_hash"] != PASSWORD
    assert row["password_hash"].startswith("scrypt:")
    assert row["is_verified"] == 0


def test_verification_link_verifies_once(app, client):
    register(client)
    link = verify_link(client)
    client.get(link)
    assert user_row(app)["is_verified"] == 1
    # The same link must not work a second time.
    again = client.get(link, follow_redirects=True).get_data(as_text=True)
    assert "not valid or has expired" in again


def test_made_up_token_is_refused(client):
    page = client.get("/verify/not-a-real-token", follow_redirects=True).get_data(as_text=True)
    assert "not valid or has expired" in page


def test_registering_twice_does_not_reveal_the_account(app, client):
    """A second sign-up with the same email shows the same page and changes nothing."""
    register(client)
    first_hash = user_row(app)["password_hash"]
    response = register(client, password="a-different-password")
    assert response.status_code == 302 and response.headers["Location"].endswith("/verify-sent")
    assert user_row(app)["password_hash"] == first_hash


def test_login_and_logout(client):
    register(client)
    client.get(verify_link(client))
    assert login(client).status_code == 302
    assert "Log out" in client.get("/").get_data(as_text=True)
    post(client, "/logout", token_from="/")
    assert "Log in" in client.get("/").get_data(as_text=True)


def test_wrong_password_gives_one_generic_message(client):
    register(client)
    wrong = login(client, password="not-the-password").get_data(as_text=True)
    unknown = login(client, email="nobody@uoguelph.ca").get_data(as_text=True)
    message = "That email or password is not right."
    assert message in wrong and message in unknown


def test_login_is_rate_limited(client):
    for _ in range(5):
        login(client, password="wrong-password-here")
    assert login(client, password="wrong-password-here").status_code == 429


def test_login_only_redirects_inside_the_site(client):
    register(client)
    client.get(verify_link(client))
    response = post(client, "/login?next=https://evil.example/", {"email": "student@uoguelph.ca", "password": PASSWORD})
    assert response.headers["Location"] == "/"


def test_post_without_csrf_token_is_refused(client):
    response = client.post("/login", data={"email": "student@uoguelph.ca", "password": PASSWORD})
    assert response.status_code == 400


def test_post_with_wrong_csrf_token_is_refused(client):
    csrf(client)    # gives the session a real token
    response = client.post("/login", data={"email": "a@uoguelph.ca", "password": PASSWORD, "csrf_token": "guess"})
    assert response.status_code == 400
