# Student Database CRUD Application

A beginner internship project using Python, FastAPI, and SQLite.
Use dummy student information only.

## Current progress

Stage 3: student schemas and input validation. SQLite storage and models for
creating, partially updating, and returning students are ready. The application
still provides only the welcome endpoint; student endpoints come in Stage 4.

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
  data/
    .gitkeep          # Keeps this empty folder in Git
  .gitignore          # Excludes local files and secrets
  requirements.txt   # Required Python packages
  tests/             # Database and schema checks with Python's unittest
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
and the same JSON response. Student endpoints do not exist yet.

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

Run the database and schema checks (these use temporary databases, leaving local
data alone):

```powershell
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
must have valid syntax. Age must be a positive integer; strings, booleans, and
fractional numbers are rejected. Unknown input fields and client-supplied `id`
or `created_at` values are rejected. Email uniqueness is enforced by SQLite,
since schemas cannot check existing records.

Example create input for the future endpoint:

```json
{"name":"Demo Student","email":"demo@example.com","age":20,"course":"Computer Science"}
```

Example partial update input:

```json
{"course":"Mathematics"}
```

These models will appear in the API documentation when student endpoints are
connected in Stage 4.

## Next stages

4. Create, list, filter, view, update, and delete endpoints.
5. Endpoint tests, validation checks, and persistence verification.
6. Complete API examples and documentation.
7. GitHub submission preparation.
8. Trainer demonstration preparation.

The core build does not include a frontend, authentication, deployment, or AI.
