# GitHub submission guide

Repository: [AgrataSharma001/student-crud-fastapi](https://github.com/AgrataSharma001/student-crud-fastapi).
The local repository already has a `main` branch and an `origin` remote. Use
the existing repository; there is no need to initialize Git again.

## Preparation verification

Local verification on 2026-10-22 with Python 3.14.2:

- Copied tracked and non-ignored untracked project files into a temporary folder.
- Created a fresh virtual environment and installed `requirements-dev.txt`.
- Confirmed `pip check` found no broken requirements and all 25 tests passed.
- Checked documentation links, whitespace, and exclusion of local generated files.

This verified the local submission candidate. It did not fetch, commit, or push
files, and does not verify what GitHub currently contains. Complete the steps
below to publish and verify the submitted commit.

## Verify before submitting

Run these commands from the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -v
git diff --check
git status --short --branch
git remote -v
```

The suite currently contains 25 tests, including persistence across separate
Python processes. All must pass. Review modified and untracked files before
adding them. The API reference and runnable demo belong in the submission.

Confirm that generated files are excluded:

```powershell
git check-ignore .venv/pyvenv.cfg data/students.db
git ls-files .venv data '*.db' '*.sqlite' '*.sqlite3' '.env' '.aws'
```

The first command should report the environment configuration and database as
ignored when present. The second should list only `data/.gitkeep` for the current
project. Ignore rules do not remove files already tracked by Git. If anything
unexpected appears, inspect it before submitting. Keep real student data,
credentials, virtual environments, caches, and database files out of the repo.

## Review and commit

Review the changes, then explicitly stage the project files:

```powershell
git diff -- README.md app docs examples .gitignore .gitattributes
git add .gitignore .gitattributes README.md requirements.txt requirements-dev.txt app tests docs examples data/.gitkeep
git diff --cached --check
git diff --cached --stat
git diff --cached
git status --short
git commit -m "Prepare student CRUD API documentation and GitHub submission"
```

`git diff` does not display untracked file contents until they are staged; review
them in the editor or in `git diff --cached`. If Git reports nothing to commit,
the files may already have been committed. Existing commits do not need rewriting.
If Git requests an author name/email, configure the identity you intend to use
for this repository and retry the commit.

## Push and record the submission

When ready to upload the reviewed commit:

```powershell
git push origin main
git rev-parse HEAD
git status --short --branch
```

If a push is rejected because the remote has newer commits, inspect the remote
changes and reconcile them before retrying. Do not force-push over others' work.
GitHub authentication is handled by your Git credentials; never put tokens in
source files or remote URLs.

Open the repository on GitHub and confirm that the README, `app/`, `tests/`,
`docs/`, `examples/`, and both requirements files appear on `main`. Check that
the latest commit matches `git rev-parse HEAD`. Share the repository URL and
commit hash with the trainer. If the repository is private, ensure the trainer
has access.

Suggested submission note (replace the hash with your pushed commit):

```text
Project: Student Database CRUD API
Repository: https://github.com/AgrataSharma001/student-crud-fastapi
Branch: main
Commit: <pushed commit hash>
Stack: Python, FastAPI, Pydantic, SQLite
Features: create, list/filter, view, partial update, and delete students
Validation: 25 automated tests, including persistence across process restarts
Setup: README.md
API reference: docs/API.md
Demo: examples/demo.py
```

## Verify a fresh clone

After pushing, open PowerShell in a separate parent directory. Choose a new
destination that does not contain an existing project:

```powershell
git clone https://github.com/AgrataSharma001/student-crud-fastapi.git student-crud-review
Set-Location student-crud-review
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

In a second PowerShell window, change to this clone and run:

```powershell
.\.venv\Scripts\python.exe examples/demo.py
```

The clone should create its own database at startup and complete the demo.
Documentation for startup, request/response examples, errors, and limitations
is in the [README](../README.md) and [API reference](API.md).
