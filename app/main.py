"""Application entry point. Run with: python -m uvicorn app.main:app --reload."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_database
from app.routers.students import router as students_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare persistent storage before accepting requests."""
    init_database()
    yield


app = FastAPI(title="Student Database CRUD API", lifespan=lifespan)
app.include_router(students_router)


@app.get("/")
def root():
    """A small endpoint to verify that the application is running."""
    return {"message": "Student CRUD API is running"}
