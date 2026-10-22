"""SQLite connection management and initial student table setup."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from collections.abc import Iterator


DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "students.db"


def get_database_path() -> Path:
    """Supply the database location; tests can override this FastAPI dependency."""
    return DATABASE_PATH


@contextmanager
def get_connection(database_path: Path = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    """Commit successful work, roll back failures, and always close the connection."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_database(database_path: Path = DATABASE_PATH) -> None:
    """Create the student table if needed, preserving existing records."""
    with get_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                age INTEGER NOT NULL CHECK (age > 0),
                course TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
