"""Verify validation boundaries and compatibility with stored student rows."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pydantic import ValidationError

from app.database import get_connection, init_database
from app.schemas import StudentCreate, StudentResponse, StudentUpdate


class StudentSchemaTests(unittest.TestCase):
    def setUp(self):
        self.student = {
            "name": "Demo Student",
            "email": "demo@example.com",
            "age": 20,
            "course": "Computer Science",
        }

    def test_create_trims_name_and_course(self):
        student = StudentCreate(**{**self.student, "name": " Demo Student ", "course": " CS "})
        self.assertEqual(student.name, "Demo Student")
        self.assertEqual(student.course, "CS")

    def test_create_requires_every_field(self):
        for field in self.student:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                StudentCreate(**{key: value for key, value in self.student.items() if key != field})

    def test_invalid_fields_are_rejected_on_create_and_update(self):
        invalid_values = {
            "name": [None, "", "   ", "a" * 101],
            "email": [None, "", "not-an-email"],
            "age": [None, 0, -1, True, 20.5, "20", 2**63],
            "course": [None, "", "   ", "a" * 101],
        }
        for field, values in invalid_values.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValidationError):
                        StudentCreate(**{**self.student, field: value})
                    with self.assertRaises(ValidationError):
                        StudentUpdate(**{field: value})

    def test_valid_boundaries(self):
        student = StudentCreate(**{**self.student, "name": "a" * 100, "course": "b" * 100, "age": 1})
        self.assertEqual(student.age, 1)

    def test_partial_update_contains_only_supplied_fields(self):
        for field, value in self.student.items():
            with self.subTest(field=field):
                update = StudentUpdate(**{field: value})
                self.assertEqual(update.model_dump(exclude_unset=True), {field: value})

    def test_empty_update_is_rejected(self):
        with self.assertRaises(ValidationError):
            StudentUpdate()

    def test_unknown_and_server_generated_input_fields_are_rejected(self):
        for field, value in {"id": 1, "created_at": "2026-01-01", "naem": "Demo"}.items():
            with self.subTest(field=field):
                with self.assertRaises(ValidationError):
                    StudentCreate(**self.student, **{field: value})
                with self.assertRaises(ValidationError):
                    StudentUpdate(**{field: value})

    def test_response_serializes_a_database_record(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "students.db"
            init_database(path)
            with get_connection(path) as connection:
                connection.execute(
                    "INSERT INTO students (name, email, age, course) VALUES (?, ?, ?, ?)",
                    tuple(self.student.values()),
                )
                row = connection.execute("SELECT * FROM students").fetchone()
            response = StudentResponse.model_validate(dict(row))
        payload = json.loads(response.model_dump_json())
        self.assertEqual(payload["id"], 1)
        self.assertEqual(payload["email"], self.student["email"])
        self.assertIsInstance(payload["created_at"], str)


if __name__ == "__main__":
    unittest.main()
