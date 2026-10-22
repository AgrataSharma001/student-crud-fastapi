"""Run with the API running: python examples/demo.py [--base-url URL]."""

import argparse
import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


def request(base_url, method, path, expected_status, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = Request(base_url + path, data=data, headers=headers, method=method)
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        content = response.read()
        if response.status != expected_status:
            raise RuntimeError(f"{method} {path}: expected {expected_status}, got {response.status}: {content!r}")
        result = json.loads(content) if content else None
        print(f"{method} {path} -> {response.status}")
        if result is not None:
            print(json.dumps(result, indent=2))
        return result


def run_demo(base_url):
    """Create a unique dummy record and remove it when the walkthrough finishes."""
    base_url = base_url.rstrip("/")
    request(base_url, "GET", "/", 200)
    body = {
        "name": "Demo Student",
        "email": f"demo-{uuid4().hex}@example.com",
        "age": 20,
        "course": "Computer Science",
    }
    student = request(base_url, "POST", "/students", 201, body)
    path = f"/students/{student['id']}"
    try:
        request(base_url, "GET", path, 200)
        query = urlencode({"name": "demo", "course": body["course"], "limit": 10, "offset": 0})
        request(base_url, "GET", "/students?" + query, 200)
        request(base_url, "POST", "/students", 409, body)
        request(base_url, "PATCH", path, 422, {"age": 0})
        request(base_url, "PATCH", path, 200, {"course": "Mathematics"})
    finally:
        request(base_url, "DELETE", path, 204)
    request(base_url, "GET", path, 404)
    print("Demo completed; the created record was deleted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    run_demo(parser.parse_args().base_url)
