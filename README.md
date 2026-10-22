# Student Database CRUD Application

A beginner internship project using Python, FastAPI, and SQLite.
Use dummy student information only.

## Current progress

Stage 7: GitHub submission preparation. The student CRUD API includes an
[API reference](docs/API.md), a runnable walkthrough, and a
[submission guide](docs/SUBMISSION.md) with review, commit, push, and fresh-clone
verification steps. Automated tests cover validation and persistence.

## Prerequisites

- Python 3.10 or newer (initial setup uses Python 3.14.2)
- Windows PowerShell
- Git, for the later GitHub submission stage

## Folder structure

```text
student-crud-fastapi/
  app/
    __init__.py       # Makes app a Python package
    main.py           # Creates the FastAPI application
    database.py       # SQLite connections and student table initialization
    schemas.py        # Student create, partial update, and response models
    routers/
      students.py     # Student CRUD endpoints
  data/
    .gitkeep          # Keeps this empty folder in Git
  .gitignore          # Excludes local files and secrets
  requirements.txt   # Required Python packages
  requirements-dev.txt # Runtime packages plus the HTTP test client
  tests/             # Database, schema, and endpoint checks
  docs/API.md        # Complete endpoint and error reference
  docs/SUBMISSION.md # GitHub submission and fresh-clone checklist
  examples/demo.py   # Runnable CRUD walkthrough using dummy data
  README.md           # Setup and usage instructions
```

The `.venv/` folder is created locally and excluded from Git. The SQLite database
lives in `data/students.db` and is also excluded from Git. Its path is resolved
relative to the project files, so it does not depend on the working directory.

## Installation (Windows PowerShell)

Open PowerShell in the repository folder:

```powershell
Set-Location "D:\python project\student-crud-fastapi"
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

A virtual environment is a separate set of Python packages for this project.
Using its Python executable directly avoids PowerShell activation restrictions.
There is no need to install SQLite separately: Python includes `sqlite3`.

Optional activation:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the explicit `.venv` executable commands
above and below. Changing your execution policy is unnecessary.

## Run the application

From the repository folder:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`app.main:app` means the `app` object inside `app/main.py`. The `--reload` option
restarts the development server when you change Python files. Press Ctrl+C to stop.

## Verify the application

With the server running, open <http://127.0.0.1:8000/> in your browser.
Expected response:

```json
{"message":"Student CRUD API is running"}
```

You can also use a second PowerShell window:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/"
```

Open <http://127.0.0.1:8000/docs> to see FastAPI's interactive API documentation.
Expand `GET /`, select **Try it out**, and select **Execute**. Expect HTTP 200
and the same JSON response. The **Students** section contains the CRUD endpoints.

See the [API reference](docs/API.md) for all fields, filters, responses, and error
examples. With the server running, execute the complete walkthrough in a second
PowerShell window:

```powershell
.\.venv\Scripts\python.exe examples/demo.py
```

It creates a unique dummy student, demonstrates CRUD and common errors, and
deletes the created record afterward. It uses the running server's database.

## Verify Stage 2 storage

Starting the server automatically creates `data/students.db` and the `students`
table if they do not exist. Restarting the server preserves existing records.
The table contains `id`, `name`, unique `email`, positive `age`, `course`, and an
automatically assigned UTC `created_at` timestamp.

Database connections commit successful transactions, roll back failed ones, and
close after use. To inspect the table after starting the server:

```powershell
@'
from app.database import get_connection

with get_connection() as db:
    for column in db.execute("PRAGMA table_info(students)"):
        print(dict(column))
'@ | .\.venv\Scripts\python.exe -
```

Run the database, schema, and endpoint checks (these use temporary databases, leaving local
data alone):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -v
```

## Stage 3 schemas

`app/schemas.py` defines three Pydantic models:

- `StudentCreate`: requires `name`, `email`, `age`, and `course`.
- `StudentUpdate`: accepts any nonempty subset of those fields. Omitted fields
  stay unchanged; explicit `null` values are rejected. Use
  `model_dump(exclude_unset=True)` to obtain only the supplied changes.
- `StudentResponse`: includes all student fields plus a positive `id` and a
  `created_at` datetime. Convert SQLite rows with
  `StudentResponse.model_validate(dict(row))`.

Names and courses are trimmed and must contain 1–100 characters. Email addresses
must have valid syntax. Age must be a positive integer within SQLite's signed
64-bit range (at most 9223372036854775807); strings, booleans, and
fractional numbers are rejected. Unknown input fields and client-supplied `id`
or `created_at` values are rejected. Email uniqueness is enforced by SQLite,
since schemas cannot check existing records.

Example create input:

```json
{"name":"Demo Student","email":"demo@example.com","age":20,"course":"Computer Science"}
```

Example partial update input:

```json
{"course":"Mathematics"}
```

These models appear in the interactive API documentation at `/docs`.

## Stage 4 endpoints

| Method | Path | Result |
| --- | --- | --- |
| POST | `/students` | Create a student (201) |
| GET | `/students` | List students ordered by ID (200) |
| GET | `/students/{student_id}` | View one student (200) |
| PATCH | `/students/{student_id}` | Update supplied fields (200) |
| DELETE | `/students/{student_id}` | Delete a student (204, empty body) |

List parameters: `name` searches a literal substring; `course` matches an exact
course. Both ignore ASCII case and can be combined. `limit` defaults to 100 and
must be 1-100; `offset` defaults to 0 and must be nonnegative. For example:
`/students?name=demo&course=Computer%20Science&limit=10&offset=0`.

Missing students return 404, duplicate emails return 409, and invalid input
returns 422. Email uniqueness follows SQLite's case-sensitive text comparison
after Pydantic email normalization. Updates preserve omitted fields. IDs and
timestamps are assigned by the database.

With the server running, create and update a dummy student from PowerShell:

```powershell
$studentBody = @{
    name = "Demo Student"
    email = "demo@example.com"
    age = 20
    course = "Computer Science"
} | ConvertTo-Json
$student = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/students" -ContentType "application/json" -Body $studentBody
Invoke-RestMethod -Uri "http://127.0.0.1:8000/students/$($student.id)"
$changes = @{ course = "Mathematics" } | ConvertTo-Json
Invoke-RestMethod -Method Patch -Uri "http://127.0.0.1:8000/students/$($student.id)" -ContentType "application/json" -Body $changes
Invoke-RestMethod -Method Delete -Uri "http://127.0.0.1:8000/students/$($student.id)"
```

## Stage 5 verification

The full suite runs with `python -m unittest discover -v` using the project
virtual environment and development dependencies shown above. Checks cover:

- Student creation, filtering, pagination, partial updates, and deletion.
- Missing records, duplicate emails, and failed writes leaving records intact.
- Missing, null, blank, oversized, and incorrectly typed input; malformed JSON;
  invalid IDs and query parameters. Invalid requests return 422.
- Literal apostrophes, SQL fragments, and wildcard characters in stored text
  and filters.
- Transaction commit, rollback, and connection cleanup.
- Create, update, conflict rollback, and deletion across five separate Python
  processes, each starting and stopping the application with the same temporary
  SQLite file. IDs, timestamps, and unchanged records are preserved.

All automated database checks use temporary files. They do not write to
`data/students.db`. Run the persistence check alone with:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persistence -v
```

## Next stages

8. Trainer demonstration preparation.

The core build does not include a frontend, authentication, deployment, or AI.
