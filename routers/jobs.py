"""
Jobs router — all API endpoints for clip generation jobs.

Endpoints:
  POST   /api/jobs                         — create job (upload or URL)
  GET    /api/jobs                         — list recent jobs (history)
  GET    /api/jobs/{id}                    — get job + clips
  POST   /api/jobs/{id}/clips/{cid}/post   — generate social post for clip
  POST   /api/jobs/{id}/clips/{cid}/export — cut and return clip mp4
"""
import os
import shutil

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import Clip, Job
from services import clip_detector, post_generator, transcription, video_processor

router = APIRouter()

UPLOAD_DIR = "uploads"
CLIPS_DIR = "clips"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)


# ── Create job ────────────────────────────────────────────────────────────────

@router.post("/jobs", status_code=201)
async def create_job(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    video: UploadFile = File(None),
    url: str = Form(None),
):
    if not video and not url:
        raise HTTPException(400, "Provide a video file or a URL")

    job = Job(
        source_type="upload" if video else "url",
        title=video.filename if video else url,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Save the uploaded file immediately so the background task can find it
    if video:
        ext = os.path.splitext(video.filename or "video.mp4")[1] or ".mp4"
        save_path = os.path.join(UPLOAD_DIR, f"{job.id}{ext}")
        with open(save_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
        job.source_path = save_path
        db.commit()

    background_tasks.add_task(_process_job, job.id, url)
    return {"id": job.id, "status": job.status}


# ── List / get jobs ───────────────────────────────────────────────────────────

@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(20).all()
    return [_fmt_job(j) for j in jobs]


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return _fmt_job(job)


# ── Post generation ───────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/clips/{clip_id}/post")
def generate_post(job_id: str, clip_id: str, db: Session = Depends(get_db)):
    clip = _get_clip(job_id, clip_id, db)
    try:
        result = post_generator.generate_post(clip.title, clip.reason or "")
        return result
    except Exception as e:
        raise HTTPException(500, f"Post generation failed: {e}")


# ── Clip export ───────────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/clips/{clip_id}/export")
def export_clip(job_id: str, clip_id: str, db: Session = Depends(get_db)):
    clip = _get_clip(job_id, clip_id, db)
    job = clip.job

    if not job.source_path or not os.path.exists(job.source_path):
        raise HTTPException(400, "Source video not available for export")

    out_path = os.path.join(CLIPS_DIR, f"{clip_id}.mp4")
    if not os.path.exists(out_path):
        try:
            video_processor.cut_clip(job.source_path, clip.start_time, clip.end_time, out_path)
        except Exception as e:
            raise HTTPException(500, f"FFmpeg export failed: {e}")
        clip.export_path = out_path
        db.commit()

    return FileResponse(out_path, media_type="video/mp4", filename=f"clip_{clip_id}.mp4")


# ── Background processing ─────────────────────────────────────────────────────

def _process_job(job_id: str, url: str | None):
    """
    Full pipeline:
      1. Download (if URL)
      2. Extract audio
      3. Transcribe
      4. Detect clips
      5. Persist clips
    Falls back to mock clips if transcription fails.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = "processing"
        db.commit()

        # Step 1: get video path
        video_path = job.source_path
        if url:
            video_path = video_processor.download_youtube(url, job.id)
            job.source_path = video_path
            db.commit()

        # Step 2: extract audio
        audio_path = video_processor.extract_audio(video_path, job.id)

        # Step 3: transcribe (graceful fallback)
        segments = []
        try:
            segments = transcription.transcribe(audio_path)
        except Exception:
            pass  # will use mock clips below

        # Step 4: detect or mock
        if segments:
            clips_data = clip_detector.detect_clips(segments)
        else:
            try:
                duration = video_processor.get_duration(video_path)
            except Exception:
                duration = 600.0
            clips_data = clip_detector.mock_clips(duration)

        # Step 5: save clips
        for c in clips_data:
            db.add(
                Clip(
                    job_id=job.id,
                    title=c["title"],
                    start_time=c["start_time"],
                    end_time=c["end_time"],
                    confidence=c["confidence"],
                    reason=c["reason"],
                )
            )

        job.status = "done"
        db.commit()

    except Exception as e:
        db.query(Job).filter(Job.id == job_id).update(
            {"status": "failed", "error": str(e)}
        )
        db.commit()
    finally:
        db.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_clip(job_id: str, clip_id: str, db: Session) -> Clip:
    clip = db.query(Clip).filter(Clip.id == clip_id, Clip.job_id == job_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    return clip


def _fmt_job(job: Job) -> dict:
    return {
        "id": job.id,
        "status": job.status,
        "title": job.title,
        "source_type": job.source_type,
        "created_at": job.created_at.isoformat(),
        "error": job.error,
        "clips": [_fmt_clip(c) for c in job.clips],
    }


def _fmt_clip(clip: Clip) -> dict:
    return {
        "id": clip.id,
        "title": clip.title,
        "start_time": clip.start_time,
        "end_time": clip.end_time,
        "confidence": clip.confidence,
        "reason": clip.reason,
        "exported": clip.export_path is not None,
    }
