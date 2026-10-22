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

    def test_invalid_create_and_update_leave_storage_unchanged(self):
        student = self.create()
        invalid_values = {
            "name": [None, "", "  ", "a" * 101],
            "email": [None, "invalid", ""],
            "age": [None, 0, -1, True, 20.5, "20", 2**63],
            "course": [None, "", "  ", "a" * 101],
        }
        for field, values in invalid_values.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    response = self.client.post("/students", json={**self.student, field: value})
                    self.assertEqual(response.status_code, 422, response.text)
                    response = self.client.patch(
                        f"/students/{student['id']}", json={"name": "Changed", field: value}
                    )
                    self.assertEqual(response.status_code, 422, response.text)
                    self.assertEqual(self.client.get("/students").json(), [student])

    def test_malformed_and_non_object_bodies_are_rejected(self):
        student = self.create()
        for method, url in [("post", "/students"), ("patch", f"/students/{student['id']}")]:
            for body in ["{", "null", "[]", '"text"', "20"]:
                with self.subTest(method=method, body=body):
                    response = getattr(self.client, method)(
                        url, content=body, headers={"Content-Type": "application/json"}
                    )
                    self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.client.get("/students").json(), [student])

    def test_all_id_routes_and_list_parameter_boundaries(self):
        for method, kwargs in [("get", {}), ("patch", {"json": {"age": 21}}), ("delete", {})]:
            for identifier in ["0", "-1", "abc", str(2**63)]:
                with self.subTest(method=method, identifier=identifier):
                    response = getattr(self.client, method)(f"/students/{identifier}", **kwargs)
                    self.assertEqual(response.status_code, 422, response.text)
        for params in [{"limit": "abc"}, {"offset": "abc"}, {"name": "a" * 101}, {"course": ""}, {"course": "a" * 101}]:
            with self.subTest(params=params):
                response = self.client.get("/students", params=params)
                self.assertEqual(response.status_code, 422, response.text)

    def test_text_is_stored_and_filtered_literally(self):
        student = self.create(name="O'Brien 100%_", course="Art's %_ Lab")
        for params in [{"name": "O'Brien"}, {"name": "%_"}, {"course": "Art's %_ Lab"}]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get("/students", params=params).json(), [student])
        self.assertEqual(self.client.get("/students", params={"course": "Art"}).json(), [])
        self.assertEqual(self.client.get("/students", params={"course": "' OR 1=1 --"}).json(), [])

    def test_valid_boundaries_and_all_fields_update(self):
        student = self.create(name="a" * 100, course="b" * 100, age=1)
        changes = {"name": " Updated ", "email": "updated@example.com", "age": 2**63 - 1, "course": " Mathematics "}
        response = self.client.patch(f"/students/{student['id']}", json=changes)
        self.assertEqual(response.status_code, 200, response.text)
        expected = {**student, **changes, "name": "Updated", "course": "Mathematics"}
        self.assertEqual(response.json(), expected)
        self.assertEqual(self.client.get(f"/students/{student['id']}").json(), expected)


if __name__ == "__main__":
    unittest.main()
