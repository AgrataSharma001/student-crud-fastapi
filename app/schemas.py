"""Validated student input and response models for the API."""

from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


StudentName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
CourseName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# Match SQLite's signed 64-bit INTEGER range before values reach the database.
StudentAge = Annotated[int, Field(strict=True, gt=0, le=2**63 - 1)]


class StudentCreate(BaseModel):
    """All student fields are required when creating a record."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{
            "name": "Demo Student", "email": "demo@example.com",
            "age": 20, "course": "Computer Science",
        }]},
    )

    name: StudentName
    email: EmailStr
    age: StudentAge
    course: CourseName


class StudentUpdate(BaseModel):
    """Partial update: omitted fields stay unchanged; explicit nulls are invalid."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"course": "Mathematics"}]},
    )

    name: StudentName | None = None
    email: EmailStr | None = None
    age: StudentAge | None = None
    course: CourseName | None = None

    @field_validator("name", "email", "age", "course", mode="before")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Omit unchanged fields instead of sending null")
        return value

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one student field to update")
        return self


class StudentResponse(StudentCreate):
    """A stored student, including the database-generated fields."""

    model_config = ConfigDict(json_schema_extra={"examples": [{
        "id": 1, "name": "Demo Student", "email": "demo@example.com",
        "age": 20, "course": "Computer Science", "created_at": "2026-10-22T12:00:00",
    }]})

    id: Annotated[int, Field(strict=True, gt=0)]
    created_at: datetime
