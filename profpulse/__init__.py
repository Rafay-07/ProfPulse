"""ProfPulse: professor ratings that are tied to a course.

create_app() builds the Flask application. It is a function (rather than a
global app object) so the tests can build a fresh copy with its own database.
"""

import os
import secrets

from flask import Flask, render_template

from . import config


def _load_secret_key(app):
    """Returns the key Flask uses to sign the session cookie.

    In production, set the PROFPULSE_SECRET_KEY environment variable.
    For local use, a random key is made once and kept in instance/secret_key,
    a folder that is never committed. No key is ever written in the code.
    """
    from_env = os.environ.get("PROFPULSE_SECRET_KEY")
    if from_env:
        return from_env
    path = os.path.join(app.instance_path, "secret_key")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf8") as handle:
            handle.write(secrets.token_hex(32))
    with open(path, encoding="utf8") as handle:
        return handle.read().strip()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "profpulse.sqlite"),
        # No real email is sent yet. While this is on, the page shown after
        # sign-up displays the verification link so the flow can be tried.
        # Set PROFPULSE_SHOW_VERIFY_LINK=0 once real email is connected.
        SHOW_VERIFY_LINK=os.environ.get("PROFPULSE_SHOW_VERIFY_LINK", "1") == "1",
        # The session cookie cannot be read by JavaScript and is not sent
        # along with requests that start on other sites.
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=64 * 1024,     # no form on this site needs more than 64 KB
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = _load_secret_key(app)

    # Database, then the groups of pages (blueprints).
    from . import auth, browse, db, reviews, security

    db.init_app(app)
    app.register_blueprint(security.bp)
    app.register_blueprint(browse.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(reviews.bp)

    # Values and helpers every template can use.
    @app.context_processor
    def template_globals():
        return {
            "csrf_token": security.csrf_token,
            "school_name": config.SCHOOL_NAME,
            "school_domain": config.SCHOOL_EMAIL_DOMAIN,
            "categories": config.CATEGORIES,
        }

    @app.template_filter("score")
    def format_score(value):
        """Shows 4.25 as "4.3", and a missing average as "n/a"."""
        return "n/a" if value is None else f"{value:.1f}"

    app.add_template_filter(config.term_label, "term_label")

    @app.after_request
    def security_headers(response):
        """Headers that tell the browser to be strict with this site.

        The content policy only allows scripts, styles and fonts from this
        site itself, so an injected <script> tag would not run.
        """
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    # One plain error page for the common problems.
    def error_page(error):
        return render_template("error.html", error=error), error.code

    for code in (400, 403, 404, 413, 429):
        app.register_error_handler(code, error_page)

    return app
