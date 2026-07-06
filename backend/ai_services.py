"""AI services: LLM story analysis, image generation, video generation, TTS."""
from __future__ import annotations
import os
import json
import base64
import uuid
import re
from pathlib import Path
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration
from emergentintegrations.llm.openai import OpenAITextToSpeech


STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "/app/backend/storage"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _api_key() -> str:
    key = os.getenv("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY is not configured")
    return key


STORY_SYSTEM_PROMPT = """You are a world-class film director and screenwriter's assistant.
You transform stories (from any source, any culture, any language) into cinema-ready blueprints.

CRITICAL COPYRIGHT & SAFETY RULES:
- NEVER use trademarked or copyrighted character designs, actors, or franchises.
- If the input mentions well-known mythological/legendary figures (e.g., Rama, Krishna, Shiva, Hanuman, Arjuna),
  create ORIGINAL character designs inspired by the archetype but distinctly YOUR OWN — do not copy any famous
  film/TV/comic depictions. Describe unique original attire, features, and props.
- Give every character a NEW original name PLUS the traditional name as an alias
  (e.g., "Ravan" -> archetype: "Warrior King", new_name: "Vikrant the Ten-Diademed").
- Avoid depicting real living people.
- Never generate sexual, violent-gore, or hateful content. Keep it PG-13.

You will return ONLY valid JSON, no markdown, no commentary. Structure:
{
  "title": "string",
  "logline": "one-sentence summary",
  "genre": "string",
  "tone": "string",
  "visual_style": "one-line cinematic style spec (lighting, palette, camera language)",
  "characters": [
    {
      "id": "char_1",
      "name": "Original creative name",
      "archetype": "e.g. warrior king, wise sage",
      "traditional_alias": "the original mythological name if any, else empty string",
      "description": "One paragraph physical + costume description that is ORIGINAL. Include age, build, skin, hair, attire, distinct props. Do not reference any real film/actor.",
      "personality": "short"
    }
  ],
  "scenes": [
    {
      "id": "scene_1",
      "title": "short scene title",
      "location": "where",
      "time_of_day": "dawn/day/dusk/night",
      "description": "3-5 sentences describing the beat visually",
      "narration": "1-3 sentences of narrator voiceover (in the same language as user's input if that language is not English, else English). Keep under 380 characters.",
      "characters": ["char_1"],
      "camera": "e.g. slow dolly in, wide establishing, overhead",
      "mood": "e.g. mysterious, triumphant",
      "image_prompt": "A DETAILED prompt for text-to-image generation, cinematic, 35mm, describing the exact frame. INCLUDE character descriptions inline so images are consistent. Original designs only.",
      "video_prompt": "A DETAILED text-to-video prompt for 4-8 second clip, describing motion, action, camera movement. Keep coherent with image_prompt."
    }
  ]
}

Aim for 4-8 scenes for a short film. Keep character count 2-5.
"""


async def analyze_story(text: str, language_hint: str = "auto") -> dict:
    """Use Claude Sonnet 4.6 to break the story into scenes and characters (JSON).

    language_hint:
      - "auto" — detect from source text
      - any language name or ISO code (e.g. "hi", "Hindi", "es", "Spanish", "Swahili")
    """
    chat = LlmChat(
        api_key=_api_key(),
        session_id=f"story-{uuid.uuid4().hex[:8]}",
        system_message=STORY_SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-6")

    lang_instruction = ""
    lh = (language_hint or "auto").strip()
    if lh and lh.lower() not in ("auto", ""):
        lang_instruction = (
            f"\n\nLANGUAGE OVERRIDE: The narrator's voice-over lines (field `narration` on every scene) "
            f"MUST be written in **{lh}** — even if the source text is in a different language. "
            f"Use the native script of that language (e.g. Devanagari for Hindi, Arabic for Arabic, "
            f"Cyrillic for Russian, Chinese characters for Mandarin/Cantonese). "
            f"Keep every other JSON field in English so the pipeline can consume it consistently."
        )
    else:
        lang_instruction = (
            "\n\nLANGUAGE: Auto-detect the source language and write the narrator's voice-over "
            "(field `narration` on every scene) in that same language using its native script. "
            "Keep every other JSON field in English."
        )

    user_prompt = f"""Transform the following source into the JSON blueprint described in your system prompt.
{lang_instruction}

Return JSON only.

SOURCE:
'''
{text[:15000]}
'''
"""
    msg = UserMessage(text=user_prompt)
    response = await chat.send_message(msg)
    # response may be a string
    raw = response if isinstance(response, str) else str(response)
    # Strip markdown fences if present
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    # Best effort extract first JSON object
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group(0))
        raise RuntimeError(f"LLM did not return valid JSON. Got: {raw[:500]}")


async def generate_image(prompt: str, out_name: str) -> str:
    """Generate an image with Gemini Nano Banana. Returns storage-relative filename."""
    chat = LlmChat(
        api_key=_api_key(),
        session_id=f"img-{uuid.uuid4().hex[:8]}",
        system_message="You are a cinematic concept artist. Generate a single high-quality image.",
    ).with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])

    msg = UserMessage(text=f"Cinematic still, ultra-detailed, film-grain, 35mm. {prompt}")
    _text, images = await chat.send_message_multimodal_response(msg)
    if not images:
        raise RuntimeError("No image returned from Nano Banana")
    img = images[0]
    image_bytes = base64.b64decode(img["data"])
    out_path = STORAGE_DIR / out_name
    out_path.write_bytes(image_bytes)
    return out_name


def generate_video_sync(prompt: str, out_name: str, size: str = "1280x720", duration: int = 4, model: str = "sora-2") -> str:
    """Generate a short video with Sora 2. Blocking call (runs in a threadpool from FastAPI)."""
    video_gen = OpenAIVideoGeneration(api_key=_api_key())
    video_bytes = video_gen.text_to_video(
        prompt=prompt,
        model=model,
        size=size,
        duration=duration,
        max_wait_time=900,
    )
    if not video_bytes:
        raise RuntimeError("Sora 2 returned no video")
    out_path = STORAGE_DIR / out_name
    video_gen.save_video(video_bytes, str(out_path))
    return out_name


async def generate_narration(text: str, out_name: str, voice: str = "onyx", model: str = "tts-1") -> str:
    """Generate narration audio with OpenAI TTS."""
    tts = OpenAITextToSpeech(api_key=_api_key())
    # Enforce 4096 char limit
    text = (text or "").strip()[:4000] or "..."
    audio_bytes = await tts.generate_speech(
        text=text,
        model=model,
        voice=voice,
        response_format="mp3",
    )
    out_path = STORAGE_DIR / out_name
    out_path.write_bytes(audio_bytes)
    return out_name
