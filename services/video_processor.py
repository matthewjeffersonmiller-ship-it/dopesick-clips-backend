"""
Video processing: download YouTube videos, extract audio, cut clips.
Uses ffmpeg — expects it in PATH or set FFMPEG_PATH in .env.
"""
import subprocess
import os
import yt_dlp

UPLOAD_DIR = "uploads"
CLIPS_DIR = "clips"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CLIPS_DIR, exist_ok=True)

# Allow overriding ffmpeg path via env (useful if not in PATH)
FFMPEG = os.getenv("FFMPEG_PATH", "ffmpeg")
FFPROBE = os.getenv("FFPROBE_PATH", "ffprobe")


def download_youtube(url: str, job_id: str) -> str:
    """Download a YouTube video to uploads/, return local path."""
    out_template = os.path.join(UPLOAD_DIR, f"{job_id}.%(ext)s")
    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # yt-dlp fills in the extension — find the downloaded file
        ext = info.get("ext", "mp4")
    path = os.path.join(UPLOAD_DIR, f"{job_id}.{ext}")
    if not os.path.exists(path):
        # Try mp4 fallback
        path = os.path.join(UPLOAD_DIR, f"{job_id}.mp4")
    return path


def extract_audio(video_path: str, job_id: str) -> str:
    """Extract mono 16kHz WAV for Whisper transcription."""
    audio_path = os.path.join(UPLOAD_DIR, f"{job_id}_audio.wav")
    subprocess.run(
        [
            FFMPEG, "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            audio_path,
        ],
        check=True,
        capture_output=True,
    )
    return audio_path


def get_duration(video_path: str) -> float:
    """Return video duration in seconds using ffprobe."""
    result = subprocess.run(
        [
            FFPROBE, "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    import json
    data = json.loads(result.stdout)
    return float(data["format"].get("duration", 600))


def cut_clip(video_path: str, start: float, end: float, out_path: str):
    """Cut a segment from video and save to out_path."""
    duration = end - start
    subprocess.run(
        [
            FFMPEG, "-y",
            "-ss", str(start),
            "-i", video_path,
            "-t", str(duration),
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            out_path,
        ],
        check=True,
        capture_output=True,
    )
