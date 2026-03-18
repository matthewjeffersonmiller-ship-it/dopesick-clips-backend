"""
GhostClips — FastAPI backend
Run: uvicorn main:app --reload --port 8000
"""
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers import jobs

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="GhostClips API", version="1.0.0")

# allow_origins=["*"] is incompatible with allow_credentials=True — browsers
# reject credentialed preflight when the server echoes back a wildcard origin.
# Explicit origins are required.
ALLOWED_ORIGINS = [
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:19006",
    "http://127.0.0.1:19006",
]

# Allow additional origins via env var (comma-separated) for Railway / production
extra = os.getenv("CORS_ORIGINS", "").strip()
if extra:
    ALLOWED_ORIGINS += [o.strip() for o in extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api")


@app.get("/")
def root():
    return {"status": "ok", "app": "GhostClips"}


@app.get("/health")
def health():
    return {"status": "healthy"}
