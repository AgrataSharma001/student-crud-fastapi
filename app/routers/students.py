"""Student endpoints backed by short-lived SQLite transactions."""

from pathlib import Path
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path as PathParam, Query, Response, status

from app.database import get_connection, get_database_path
from app.schemas import StudentCreate, StudentResponse, StudentUpdate


router = APIRouter(prefix="/students", tags=["Students"])
DatabasePath = Annotated[Path, Depends(get_database_path)]
StudentId = Annotated[int, PathParam(gt=0, le=2**63 - 1)]


def require_student(connection: sqlite3.Connection, student_id: int) -> dict:
    row = connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return dict(row)


def handle_integrity_error(error: sqlite3.IntegrityError) -> None:
    if "UNIQUE constraint failed: students.email" in str(error):
        raise HTTPException(status_code=409, detail="Email is already registered") from error
    raise error


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(student: StudentCreate, database_path: DatabasePath):
    try:
        with get_connection(database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO students (name, email, age, course) VALUES (?, ?, ?, ?)",
                (student.name, student.email, student.age, student.course),
            )
            result = require_student(connection, cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        handle_integrity_error(error)
    return result


@router.get("", response_model=list[StudentResponse])
def list_students(
    database_path: DatabasePath,
    name: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    course: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0, le=2**63 - 1)] = 0,
):
    """Filter by a name substring and/or exact course, ignoring ASCII case."""
    conditions = []
    parameters = []
    if name is not None:
        conditions.append("instr(lower(name), lower(?)) > 0")
        parameters.append(name)
    if course is not None:
        conditions.append("course = ? COLLATE NOCASE")
        parameters.append(course)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    with get_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM students" + where + " ORDER BY id LIMIT ? OFFSET ?",
            [*parameters, limit, offset],
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: StudentId, database_path: DatabasePath):
    with get_connection(database_path) as connection:
        return require_student(connection, student_id)


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(student_id: StudentId, student: StudentUpdate, database_path: DatabasePath):
    changes = student.model_dump(exclude_unset=True)
    # Column names come only from the validated schema; values stay parameterized.
    assignments = ", ".join(f"{column} = ?" for column in changes)
    try:
        with get_connection(database_path) as connection:
            cursor = connection.execute(
                f"UPDATE students SET {assignments} WHERE id = ?",
                [*changes.values(), student_id],
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Student not found")
            result = require_student(connection, student_id)
    except sqlite3.IntegrityError as error:
        handle_integrity_error(error)
    return result


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: StudentId, database_path: DatabasePath):
    with get_connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM students WHERE id = ?", (student_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Student not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
