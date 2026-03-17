"""
Dopesick Clips — FastAPI backend
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

app = FastAPI(title="Dopesick Clips API", version="1.0.0")

# Allow all origins for local dev — lock this down before production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api")


@app.get("/")
def root():
    return {"status": "ok", "app": "Dopesick Clips"}


@app.get("/health")
def health():
    return {"status": "healthy"}
