"""Check SQLite initialization, persistence, and transaction handling."""

from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from app.database import get_connection, init_database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "data" / "students.db"
        init_database(self.path)

    def insert_student(self, connection, email="demo@example.com", age=20):
        connection.execute(
            "INSERT INTO students (name, email, age, course) VALUES (?, ?, ?, ?)",
            ("Demo Student", email, age, "Computer Science"),
        )

    def test_records_survive_reinitialization_and_new_connection(self):
        with get_connection(self.path) as connection:
            self.insert_student(connection)
        init_database(self.path)
        with get_connection(self.path) as connection:
            rows = connection.execute("SELECT * FROM students").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Demo Student")
        self.assertIsInstance(rows[0]["id"], int)
        self.assertTrue(rows[0]["created_at"])

    def test_duplicate_email_rolls_back_transaction(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with get_connection(self.path) as connection:
                self.insert_student(connection)
                self.insert_student(connection)
        with get_connection(self.path) as connection:
            count = connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        self.assertEqual(count, 0)

    def test_non_positive_age_is_rejected(self):
        for age in (0, -1):
            with self.subTest(age=age), self.assertRaises(sqlite3.IntegrityError):
                with get_connection(self.path) as connection:
                    self.insert_student(connection, age=age)

    def test_unexpected_exception_rolls_back_and_closes_connection(self):
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            with get_connection(self.path) as connection:
                self.insert_student(connection)
                raise RuntimeError("interrupted")
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
        with get_connection(self.path) as reopened:
            count = reopened.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        self.assertEqual(count, 0)

    def test_successful_connection_is_closed_after_commit(self):
        with get_connection(self.path) as connection:
            self.insert_student(connection)
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
        with get_connection(self.path) as reopened:
            count = reopened.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
