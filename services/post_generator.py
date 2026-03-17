"""
Social post text generation via OpenAI.
Returns TikTok caption, YouTube title, hashtags, and short description.
"""
import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM = """You are a social media expert writing for a creator named Dopesick Matt.
Brand: raw, real, dark, reflective, confident, underground, chaotic, funny, emotional, internet-native. Never corporate.
Title style: mostly lowercase; key reaction words FULL CAPS; 2-4 words with weird mixed casing (tHis, wHaT); use -- for pauses; no period at end.
Good title examples: "bro WHAT was tHaT", "dId A dUnGeOn -- wtFf", "nahhhh BRO"
Bad title examples: "Insane Dungeon Run!", "Epic Gaming Moment!"
"""


def generate_post(clip_title: str, clip_reason: str) -> dict:
    """
    Generate platform-ready post content for a clip.
    Returns dict with tiktok_caption, youtube_title, hashtags, post_description.
    """
    prompt = f"""Create social post content for this clip:
Title hint: {clip_title}
Context: {clip_reason}

Return ONLY valid JSON (no markdown fences):
{{
  "tiktok_caption": "short punchy 1-2 sentence caption in creator voice",
  "youtube_title": "40 chars max, weird mixed casing, no period",
  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],
  "post_description": "2-3 raw, real sentences describing the clip moment"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.85,
    )

    return json.loads(response.choices[0].message.content)
