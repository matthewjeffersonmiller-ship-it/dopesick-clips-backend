"""
Clip moment detection from transcript segments.

Algorithm:
  1. Slide a window forward collecting segments until window is 15–55s
  2. Score each window by excitement signals
  3. Enforce 30s diversity spacing between clip starts
  4. Return top N clips sorted by score
"""

# Words that suggest an exciting or reactive moment
EXCITEMENT_WORDS = {
    "wait", "what", "no", "yes", "bro", "omg", "dude", "crazy", "insane",
    "actually", "literally", "holy", "wtf", "damn", "fire", "lets go",
    "nah", "nope", "wow", "impossible", "unbelievable", "clutch", "dead",
    "goat", "peak", "based", "honestly", "never", "always", "hate", "love",
    "perfect", "terrible", "amazing", "awful", "real talk", "bruh", "cap",
    "no cap", "lowkey", "highkey", "facts", "bet", "gg", "rip",
}

MIN_CLIP_SECONDS = 12
MAX_CLIP_SECONDS = 55
MIN_SCORE = 1.0
DIVERSITY_GAP = 30  # min seconds between clip start times


def _score(segments: list[dict]) -> float:
    if not segments:
        return 0.0
    text = " ".join(s["text"] for s in segments).lower()
    word_count = len(text.split())
    if word_count < 5:
        return 0.0

    duration = segments[-1]["end"] - segments[0]["start"]
    speech_rate = word_count / max(duration, 1)

    excitement = sum(1 for w in EXCITEMENT_WORDS if w in text)
    questions = text.count("?")
    exclamations = text.count("!")
    rate_bonus = min(speech_rate / 2.5, 1.0) * 2.0  # cap at 2

    return round(excitement * 1.5 + questions + exclamations + rate_bonus, 2)


def _title_from_text(text: str) -> str:
    words = text.strip().split()[:7]
    return " ".join(words).rstrip(".,!?") + "..."


def _reason(segments: list[dict], score: float) -> str:
    text = " ".join(s["text"] for s in segments).lower()
    hits = [w for w in EXCITEMENT_WORDS if w in text]
    kw = f"keywords: {', '.join(hits[:4])}" if hits else "high speech density"
    return f"Score {score:.1f} — {kw}"


def detect_clips(segments: list[dict], max_clips: int = 5) -> list[dict]:
    """Build clip windows from transcript segments and return top N."""
    if not segments:
        return []

    results = []
    used_starts: list[float] = []

    for i in range(len(segments)):
        window = []
        for j in range(i, len(segments)):
            window.append(segments[j])
            duration = segments[j]["end"] - segments[i]["start"]
            if duration >= MIN_CLIP_SECONDS:
                break

        if len(window) < 2:
            continue

        start = window[0]["start"]
        end = window[-1]["end"]
        duration = end - start

        if duration < MIN_CLIP_SECONDS or duration > MAX_CLIP_SECONDS:
            continue

        # Skip if too close to an already-selected clip
        if any(abs(start - u) < DIVERSITY_GAP for u in used_starts):
            continue

        score = _score(window)
        if score < MIN_SCORE:
            continue

        text = " ".join(s["text"] for s in window)
        results.append(
            {
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "title": _title_from_text(text),
                "confidence": round(min(score / 10.0, 1.0), 2),
                "reason": _reason(window, score),
            }
        )
        used_starts.append(start)

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results[:max_clips]


def mock_clips(duration_seconds: float = 600.0, count: int = 5) -> list[dict]:
    """
    Fallback clips when transcription is unavailable.
    Spreads evenly across the video.
    """
    step = duration_seconds / (count + 1)
    clips = []
    for i in range(count):
        start = round((i + 0.5) * step, 2)
        end = round(min(start + 30, duration_seconds), 2)
        clips.append(
            {
                "start_time": start,
                "end_time": end,
                "title": f"Moment {i + 1}...",
                "confidence": 0.4,
                "reason": "Auto-generated (transcript unavailable)",
            }
        )
    return clips
