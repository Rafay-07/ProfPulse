"""Starts ProfPulse on this computer.

    python run.py

Then open http://127.0.0.1:5000

The first time it runs, the database is created and filled with made-up
sample data. To start over, delete the instance folder and run it again.
"""

import os

from profpulse import create_app
from profpulse.db import database_is_empty, init_db
from profpulse.seed import seed

app = create_app()

# Build and fill the database if it is not there yet.
with app.app_context():
    if database_is_empty():
        init_db()
        seed()
        print("Created the database with sample data.")

if __name__ == "__main__":
    # Flask's debug mode shows detailed errors in the browser. It is off
    # unless you ask for it, and it must never be on for a public site.
    #   Windows PowerShell:  $env:PROFPULSE_DEBUG = "1"; python run.py
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PROFPULSE_PORT", "5000")),
        debug=os.environ.get("PROFPULSE_DEBUG") == "1",
    )
