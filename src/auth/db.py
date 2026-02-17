"""SQLite database utilities for authentication.

Uses Flask's g object for request-scoped database connections.
Database file stored in instance/users.db by default.
"""

import sqlite3
from pathlib import Path
from flask import current_app, g


def get_db():
    """Get database connection from Flask g object.

    Creates connection if not exists. Sets row_factory to sqlite3.Row
    for dict-like access to columns.
    """
    if "db" not in g:
        db_path = current_app.config.get("DATABASE", Path("instance/users.db"))
        # Ensure instance directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        g.db = sqlite3.connect(
            str(db_path),
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        # Enable foreign key constraints
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(e=None):
    """Close database connection if open.

    Registered with app.teardown_appcontext to auto-close after each request.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Execute schema.sql to create tables."""
    db = get_db()
    schema_path = Path(__file__).parent.parent.parent / "instance" / "schema.sql"

    with open(schema_path, "r") as f:
        db.executescript(f.read())


def init_app(app):
    """Register database utilities with Flask app.

    Registers close_db teardown and adds 'flask init-db' CLI command.
    """
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Clear existing data and create new tables."""
        init_db()
        print("Initialized the database.")
