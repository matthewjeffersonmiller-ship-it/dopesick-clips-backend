"""
Audio transcription via OpenAI Whisper API.
Returns list of segments: [{start, end, text}, ...]
"""
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def transcribe(audio_path: str) -> list[dict]:
    """
    Transcribe audio file using OpenAI whisper-1.
    Returns timestamped segments.
    """
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = []
    for seg in response.segments:
        segments.append(
            {
                "start": float(seg.start),
                "end": float(seg.end),
                "text": seg.text.strip(),
            }
        )
    return segments
