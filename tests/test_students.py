"""Exercise student endpoints over HTTP with isolated SQLite storage."""

from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import get_database_path, init_database
from app.main import app


class StudentEndpointTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.path = Path(stack.enter_context(TemporaryDirectory())) / "students.db"
        app.dependency_overrides[get_database_path] = lambda: self.path
        stack.callback(app.dependency_overrides.pop, get_database_path)
        stack.enter_context(patch("app.main.init_database", lambda: init_database(self.path)))
        self.client = stack.enter_context(TestClient(app))
        self.student = {
            "name": "Demo Student",
            "email": "demo@example.com",
            "age": 20,
            "course": "Computer Science",
        }

    def create(self, **changes):
        response = self.client.post("/students", json={**self.student, **changes})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_full_student_lifecycle(self):
        self.assertEqual(self.client.get("/students").json(), [])
        student = self.create(name=" Demo Student ")
        self.assertEqual(student["name"], "Demo Student")
        self.assertIn("created_at", student)
        url = f"/students/{student['id']}"
        self.assertEqual(self.client.get(url).json(), student)
        self.assertEqual(self.client.get("/students").json(), [student])
        response = self.client.patch(url, json={"course": "Mathematics"})
        self.assertEqual(response.status_code, 200, response.text)
        expected = {**student, "course": "Mathematics"}
        self.assertEqual(response.json(), expected)
        self.assertEqual(self.client.get(url).json(), expected)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get("/students").json(), [])

    def test_duplicate_email_conflicts_preserve_records(self):
        first = self.create()
        second = self.create(email="second@example.com")
        response = self.client.post("/students", json=self.student)
        self.assertEqual(response.status_code, 409, response.text)
        response = self.client.patch(
            f"/students/{second['id']}", json={"email": first["email"], "name": "Changed"}
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.client.get(f"/students/{second['id']}").json(), second)
        # Keeping the existing email is a valid update.
        self.assertEqual(
            self.client.patch(f"/students/{first['id']}", json={"email": first["email"]}).status_code,
            200,
        )
        self.assertEqual(len(self.client.get("/students").json()), 2)

    def test_missing_students(self):
        for method, kwargs in [("get", {}), ("patch", {"json": {"age": 21}}), ("delete", {})]:
            with self.subTest(method=method):
                response = getattr(self.client, method)("/students/999", **kwargs)
                self.assertEqual(response.status_code, 404, response.text)
                self.assertEqual(response.json()["detail"], "Student not found")

    def test_filters_and_pagination(self):
        first = self.create(name="Alice", course="Mathematics")
        second = self.create(name="Alicia", email="alicia@example.com")
        self.create(name="Bob", email="bob@example.com")
        response = self.client.get("/students", params={"name": "ALI"})
        self.assertEqual(response.json(), [first, second])
        response = self.client.get("/students", params={"name": "ali", "course": "mathematics"})
        self.assertEqual(response.json(), [first])
        self.assertEqual(self.client.get("/students", params={"limit": 1, "offset": 1}).json(), [second])
        self.assertEqual(self.client.get("/students", params={"offset": 10}).json(), [])
        # User text is literal data, including SQL fragments and LIKE wildcards.
        for name in ["' OR 1=1 --", "%", "_"]:
            self.assertEqual(self.client.get("/students", params={"name": name}).json(), [])

    def test_request_validation(self):
        student = self.create()
        for payload in [{}, {"age": 0}, {"age": "20"}, {"name": " "}, {"email": "bad"}, {"course": None}, {"id": 99}]:
            with self.subTest(payload=payload):
                self.assertEqual(
                    self.client.patch(f"/students/{student['id']}", json=payload).status_code, 422
                )
        self.assertEqual(self.client.post("/students", json={}).status_code, 422)
        for identifier in ["0", "-1", "invalid", str(2**63)]:
            self.assertEqual(self.client.get(f"/students/{identifier}").status_code, 422)
        for params in [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 2**63}, {"name": ""}]:
            self.assertEqual(self.client.get("/students", params=params).status_code, 422)
        self.assertEqual(self.client.get(f"/students/{student['id']}").json(), student)

    def test_existing_welcome_and_documentation(self):
        self.assertEqual(self.client.get("/").json(), {"message": "Student CRUD API is running"})
        schema = self.client.get("/openapi.json").json()
        self.assertEqual(set(schema["paths"]["/students"]), {"get", "post"})
        self.assertEqual(set(schema["paths"]["/students/{student_id}"]), {"get", "patch", "delete"})


if __name__ == "__main__":
    unittest.main()
