from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routes.tasks import router as tasks_router

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Task Manager API",
    description="A SQLite-backed task manager with filtering and a Streamlit client.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(tasks_router)

@app.get("/", tags=["Health"])
def health_check():
    return {"message": "Task Manager API is running"}
