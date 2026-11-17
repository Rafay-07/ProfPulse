"""Database access.

Every page asks for the connection with get_db(). Flask keeps one
connection per request and closes it when the request ends.

Every query in this project passes its values as "?" parameters. User input
is never glued into the SQL text, which is what stops SQL injection.
"""

import sqlite3

import click
from flask import current_app, g


def get_db():
    """Returns this request's database connection, opening it if needed."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row          # rows act like dictionaries
        g.db.execute("PRAGMA foreign_keys = ON")  # SQLite leaves this off by default
    return g.db


def close_db(error=None):
    """Closes the connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Builds every table from schema.sql. This erases existing data."""
    db = get_db()
    with current_app.open_resource("schema.sql") as schema:
        db.executescript(schema.read().decode("utf8"))


def database_is_empty():
    """True when the tables are missing or there are no professors yet."""
    try:
        count = get_db().execute("SELECT COUNT(*) FROM professors").fetchone()[0]
    except sqlite3.OperationalError:    # the table does not exist
        return True
    return count == 0


@click.command("init-db")
def init_db_command():
    """flask --app profpulse init-db : wipe the database and rebuild it."""
    init_db()
    click.echo("Database rebuilt. It is empty: run the seed command to add sample data.")


@click.command("seed")
def seed_command():
    """flask --app profpulse seed : add the made-up sample data."""
    from .seed import seed

    seed()
    click.echo("Sample data added.")


def init_app(app):
    """Hooks the database into the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
