"""Check committed API changes across completely separate Python processes."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import textwrap
import unittest


REQUEST_WORKER = textwrap.dedent("""\
    import json
    from pathlib import Path
    import sys
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from app.database import get_database_path, init_database
    from app.main import app

    path = Path(sys.argv[1])
    app.dependency_overrides[get_database_path] = lambda: path
    with patch('app.main.init_database', lambda: init_database(path)):
        with TestClient(app) as client:
            results = []
            for method, url, kwargs in json.loads(sys.argv[2]):
                response = client.request(method, url, **kwargs)
                results.append([response.status_code, response.json() if response.content else None])
    print(json.dumps(results))
""")


class PersistenceTests(unittest.TestCase):
    def request_in_new_process(self, path, requests):
        result = subprocess.run(
            [sys.executable, "-c", REQUEST_WORKER, str(path), json.dumps(requests)],
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_create_update_conflict_and_delete_survive_process_restarts(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "data" / "students.db"
            payload = {"name": "Demo", "email": "demo@example.com", "age": 20, "course": "CS"}
            created = self.request_in_new_process(path, [("POST", "/students", {"json": payload})])
            self.assertEqual(created[0][0], 201)
            first = created[0][1]
            url = f"/students/{first['id']}"

            restarted = self.request_in_new_process(path, [
                ("GET", url, {}),
                ("PATCH", url, {"json": {"course": "Mathematics"}}),
                ("POST", "/students", {"json": {**payload, "email": "second@example.com"}}),
            ])
            self.assertEqual(restarted[0], [200, first])
            updated = {**first, "course": "Mathematics"}
            self.assertEqual(restarted[1], [200, updated])
            self.assertEqual(restarted[2][0], 201)
            second = restarted[2][1]
            second_url = f"/students/{second['id']}"

            conflicts = self.request_in_new_process(path, [
                ("GET", "/students", {}),
                ("PATCH", second_url, {"json": {"email": first["email"], "name": "Changed"}}),
                ("POST", "/students", {"json": payload}),
            ])
            self.assertEqual(conflicts[0], [200, [updated, second]])
            self.assertEqual([item[0] for item in conflicts[1:]], [409, 409])

            deleted = self.request_in_new_process(path, [
                ("GET", second_url, {}),
                ("DELETE", url, {}),
            ])
            self.assertEqual(deleted, [[200, second], [204, None]])
            final = self.request_in_new_process(path, [
                ("GET", url, {}), ("GET", "/students", {}), ("DELETE", url, {}),
            ])
            self.assertEqual(final[0][0], 404)
            self.assertEqual(final[1], [200, [second]])
            self.assertEqual(final[2][0], 404)


if __name__ == "__main__":
    unittest.main()
