"""Security helpers used by every page.

Four things live here:
  1. loading the logged-in user for each request
  2. CSRF protection for every form
  3. the "you must be logged in" and "you must be verified" checks
  4. rate limits
"""

import functools
import hmac
import secrets
import time

from flask import Blueprint, abort, flash, g, redirect, request, session, url_for

from .db import get_db

bp = Blueprint("security", __name__)


# --- 1. Who is logged in ------------------------------------------------------

@bp.before_app_request
def load_logged_in_user():
    """Runs before every request. Puts the user row, or None, on g.user."""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            "SELECT id, email, is_verified FROM users WHERE id = ?", (user_id,)
        ).fetchone()


# --- 2. CSRF ------------------------------------------------------------------
#
# CSRF is when another website makes your browser submit a form to this one
# while you are logged in. The defence: every form carries a secret token
# that only this site's own pages know. A POST without the right token is
# refused.

def csrf_token():
    """Returns this visitor's token, making one on first use."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@bp.before_app_request
def check_csrf():
    """Refuses any POST that does not carry the right token."""
    if request.method != "POST":
        return
    sent = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    # compare_digest takes the same time whether the strings match or not,
    # so the comparison leaks nothing about the token.
    if not sent or not hmac.compare_digest(sent.encode(), expected.encode()):
        abort(400, "This form has expired. Go back, reload the page and try again.")


# --- 3. Access checks ---------------------------------------------------------

def safe_next(target):
    """Only allows redirects to pages on this site.

    Without this check, a link like /login?next=https://evil.example could
    send someone to another site right after they log in.
    """
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("browse.home")


def login_required(view):
    """Decorator: the page needs a logged-in user."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Log in to do that.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def verified_required(view):
    """Decorator: the page needs a logged-in user with a verified school email."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Log in to do that.", "error")
            return redirect(url_for("auth.login", next=request.path))
        if not g.user["is_verified"]:
            flash("Verify your school email before posting.", "error")
            return redirect(url_for("auth.verify_sent"))
        return view(*args, **kwargs)
    return wrapped


# --- 4. Rate limits -----------------------------------------------------------
#
# Each limited action writes a row to rate_events. To check a limit, count
# the recent rows for that action and that person.

def too_many(action, who, limit):
    """True when `who` has already done `action` the allowed number of times."""
    allowed, window_seconds = limit
    count = get_db().execute(
        "SELECT COUNT(*) FROM rate_events WHERE action = ? AND who = ? AND created_at >= ?",
        (action, str(who), time.time() - window_seconds),
    ).fetchone()[0]
    return count >= allowed


def record_event(action, who):
    """Logs one use of a limited action, and clears out rows older than two days."""
    db = get_db()
    db.execute(
        "INSERT INTO rate_events (action, who, created_at) VALUES (?, ?, ?)",
        (action, str(who), time.time()),
    )
    db.execute("DELETE FROM rate_events WHERE created_at < ?", (time.time() - 2 * 24 * 60 * 60,))
    db.commit()


def client_address():
    """The visitor's IP address, used as the "who" for people who are not logged in."""
    return request.remote_addr or "unknown"
