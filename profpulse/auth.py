"""Accounts: sign up, verify the school email, log in, log out.

How verification works:
  1. Signing up makes an account that is not verified yet.
  2. A random token is made. Only a hash of it is stored in the database.
  3. A link containing the token goes to the school email address.
  4. Opening the link proves the person can read that inbox, so the account
     is marked verified. Only verified accounts can post.

Real email is not connected yet. Until it is, the "email" is written to
instance/outbox.txt and, in development, shown on the page after sign-up.
"""

import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from . import config
from .db import get_db
from .security import client_address, record_event, safe_next, too_many

bp = Blueprint("auth", __name__)

# Rough shape of an email address. The real test is the verification link.
EMAIL_SHAPE = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")

# Checked when a login names an account that does not exist, so that case
# takes about as long as a wrong password. This hides which emails have accounts.
DUMMY_HASH = generate_password_hash("not a real password")


def _hash_token(token):
    """The database stores this hash, never the token itself. If the database
    leaked, the hashes could not be used to verify anyone's account."""
    return hashlib.sha256(token.encode()).hexdigest()


def _now():
    return datetime.now(timezone.utc)


def _start_verification(user_id, email):
    """Makes a fresh token for the user and "sends" the link."""
    token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(hours=config.VERIFY_LINK_HOURS)
    db = get_db()
    db.execute(
        "UPDATE users SET verify_token = ?, verify_expires = ? WHERE id = ?",
        (_hash_token(token), expires.isoformat(), user_id),
    )
    db.commit()
    link = url_for("auth.verify", token=token, _external=True)
    _send_verification_email(email, link)
    if current_app.config["SHOW_VERIFY_LINK"]:
        session["dev_verify_link"] = link


def _send_verification_email(email, link):
    """Stand-in for sending an email.

    To connect real email later, replace the body of this function with a
    call to an email service. Nothing else in the app needs to change.
    """
    outbox = os.path.join(current_app.instance_path, "outbox.txt")
    with open(outbox, "a", encoding="utf8") as handle:
        handle.write(f"{_now().isoformat()}  To: {email}\n  Verify your ProfPulse account: {link}\n\n")
    current_app.logger.info("Verification link for %s written to instance/outbox.txt", email)


@bp.route("/register", methods=("GET", "POST"))
def register():
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        error = None

        if too_many("register", client_address(), config.REGISTER_LIMIT):
            error = "Too many sign-ups from this connection. Try again in an hour."
        elif not EMAIL_SHAPE.match(email) or not email.endswith("@" + config.SCHOOL_EMAIL_DOMAIN):
            error = f"Use your @{config.SCHOOL_EMAIL_DOMAIN} email address."
        elif not config.PASSWORD_MIN_CHARS <= len(password) <= config.PASSWORD_MAX_CHARS:
            error = f"The password needs at least {config.PASSWORD_MIN_CHARS} characters."
        elif password != request.form.get("confirm", ""):
            error = "The two passwords do not match."

        if error is None:
            record_event("register", client_address())
            db = get_db()
            existing = db.execute("SELECT id, is_verified FROM users WHERE email = ?", (email,)).fetchone()
            if existing is None:
                # generate_password_hash salts the password and runs scrypt on it.
                cursor = db.execute(
                    "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                    (email, generate_password_hash(password)),
                )
                db.commit()
                _start_verification(cursor.lastrowid, email)
            # If the address already has an account, nothing is changed and the
            # same page is shown. The form never reveals which emails are registered.
            session["pending_email"] = email
            return redirect(url_for("auth.verify_sent"))

        flash(error, "error")
    return render_template("register.html", email=email, min_chars=config.PASSWORD_MIN_CHARS)


@bp.route("/verify-sent")
def verify_sent():
    """The "check your email" page."""
    return render_template(
        "verify_sent.html",
        email=session.get("pending_email") or (g.user["email"] if g.user else None),
        dev_link=session.pop("dev_verify_link", None),
        hours=config.VERIFY_LINK_HOURS,
    )


@bp.route("/verify/<token>")
def verify(token):
    """The page the emailed link opens."""
    db = get_db()
    user = db.execute(
        "SELECT id, verify_expires FROM users WHERE verify_token = ?", (_hash_token(token),)
    ).fetchone()
    if user is None or datetime.fromisoformat(user["verify_expires"]) < _now():
        flash("That link is not valid or has expired. Log in to get a new one.", "error")
        return redirect(url_for("auth.login"))

    # Each link works once: the token is cleared as the account is verified.
    db.execute(
        "UPDATE users SET is_verified = 1, verify_token = NULL, verify_expires = NULL WHERE id = ?",
        (user["id"],),
    )
    db.commit()
    session.pop("pending_email", None)
    flash("Your school email is verified. Log in to post a review.", "ok")
    return redirect(url_for("auth.login"))


@bp.route("/resend", methods=("POST",))
def resend():
    """Sends a new link to a logged-in user who is not verified yet."""
    if g.user is None:
        return redirect(url_for("auth.login"))
    if g.user["is_verified"]:
        return redirect(url_for("browse.home"))
    if too_many("resend", g.user["id"], (3, 60 * 60)):
        flash("A link was sent recently. Try again later.", "error")
    else:
        record_event("resend", g.user["id"])
        _start_verification(g.user["id"], g.user["email"])
        flash("A new link is on its way.", "ok")
    return redirect(url_for("auth.verify_sent"))


@bp.route("/login", methods=("GET", "POST"))
def login():
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if too_many("login-failed", client_address(), config.LOGIN_LIMIT):
            flash("Too many failed logins. Wait 15 minutes and try again.", "error")
            return render_template("login.html", email=email), 429

        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        stored_hash = user["password_hash"] if user else DUMMY_HASH
        if user is None or not check_password_hash(stored_hash, password):
            record_event("login-failed", client_address())
            # One message for both cases, so the form does not reveal
            # whether the email has an account.
            flash("That email or password is not right.", "error")
        else:
            # Start a clean session on login so an old session cannot be reused.
            session.clear()
            session["user_id"] = user["id"]
            if not user["is_verified"]:
                return redirect(url_for("auth.verify_sent"))
            return redirect(safe_next(request.args.get("next")))
    return render_template("login.html", email=email)


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    return redirect(url_for("browse.home"))
