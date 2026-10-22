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
NOT_FOUND = {
    "description": "No student exists with this ID.",
    "content": {"application/json": {"example": {"detail": "Student not found"}}},
}
EMAIL_CONFLICT = {
    "description": "Another student already uses this email.",
    "content": {"application/json": {"example": {"detail": "Email is already registered"}}},
}


def require_student(connection: sqlite3.Connection, student_id: int) -> dict:
    row = connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return dict(row)


def handle_integrity_error(error: sqlite3.IntegrityError) -> None:
    if "UNIQUE constraint failed: students.email" in str(error):
        raise HTTPException(status_code=409, detail="Email is already registered") from error
    raise error


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED,
             responses={409: EMAIL_CONFLICT})
def create_student(student: StudentCreate, database_path: DatabasePath):
    """Create a student. All four fields are required; extra fields are rejected."""
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
    name: Annotated[str | None, Query(min_length=1, max_length=100, description="Literal name substring; ignores ASCII case.")] = None,
    course: Annotated[str | None, Query(min_length=1, max_length=100, description="Exact course match; ignores ASCII case.")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of students to return.")] = 100,
    offset: Annotated[int, Query(ge=0, le=2**63 - 1, description="Number of matching students to skip.")] = 0,
):
    """Return an array ordered by ID. Filters combine with AND; no matches return []."""
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


@router.get("/{student_id}", response_model=StudentResponse, responses={404: NOT_FOUND})
def get_student(student_id: StudentId, database_path: DatabasePath):
    """Return one student, including the database-generated ID and creation time."""
    with get_connection(database_path) as connection:
        return require_student(connection, student_id)


@router.patch("/{student_id}", response_model=StudentResponse,
              responses={404: NOT_FOUND, 409: EMAIL_CONFLICT})
def update_student(student_id: StudentId, student: StudentUpdate, database_path: DatabasePath):
    """Update supplied fields only. Send at least one field; nulls are rejected."""
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


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT,
               responses={404: NOT_FOUND})
def delete_student(student_id: StudentId, database_path: DatabasePath):
    """Delete one student. Success has an empty body; repeating deletion returns 404."""
    with get_connection(database_path) as connection:
        cursor = connection.execute("DELETE FROM students WHERE id = ?", (student_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Student not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
