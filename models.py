from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import uuid


def _id():
    return str(uuid.uuid4())[:8]


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=_id)
    status = Column(String, default="queued")   # queued | processing | done | failed
    source_type = Column(String)                # upload | url
    source_path = Column(String, nullable=True) # local file path
    title = Column(String, nullable=True)       # filename or URL
    created_at = Column(DateTime, default=datetime.utcnow)
    error = Column(Text, nullable=True)

    clips = relationship("Clip", back_populates="job", cascade="all, delete-orphan")


class Clip(Base):
    __tablename__ = "clips"

    id = Column(String, primary_key=True, default=_id)
    job_id = Column(String, ForeignKey("jobs.id"))
    title = Column(String)
    start_time = Column(Float)
    end_time = Column(Float)
    confidence = Column(Float)
    reason = Column(Text, nullable=True)
    export_path = Column(String, nullable=True)

    job = relationship("Job", back_populates="clips")
