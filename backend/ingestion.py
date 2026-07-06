"""Ingestion utilities: parse PDF/DOCX/TXT files, URLs, and voice via Whisper."""
from __future__ import annotations
import io
import os
import re
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document


# ---- ISO 639-1 mapping for the world's most-spoken languages ----
# Whisper accepts these 2-letter codes; we accept full names and route to code.
_ISO_MAP = {
    "afrikaans": "af", "albanian": "sq", "amharic": "am", "arabic": "ar", "armenian": "hy",
    "assamese": "as", "azerbaijani": "az", "bashkir": "ba", "basque": "eu", "belarusian": "be",
    "bengali": "bn", "bosnian": "bs", "breton": "br", "bulgarian": "bg", "burmese": "my",
    "cantonese": "yue", "catalan": "ca", "chinese": "zh", "mandarin": "zh", "croatian": "hr",
    "czech": "cs", "danish": "da", "dutch": "nl", "english": "en", "estonian": "et",
    "faroese": "fo", "finnish": "fi", "french": "fr", "galician": "gl", "georgian": "ka",
    "german": "de", "greek": "el", "gujarati": "gu", "haitian": "ht", "hausa": "ha",
    "hawaiian": "haw", "hebrew": "he", "hindi": "hi", "hungarian": "hu", "icelandic": "is",
    "indonesian": "id", "italian": "it", "japanese": "ja", "javanese": "jv", "kannada": "kn",
    "kazakh": "kk", "khmer": "km", "korean": "ko", "lao": "lo", "latin": "la", "latvian": "lv",
    "lingala": "ln", "lithuanian": "lt", "luxembourgish": "lb", "macedonian": "mk",
    "malagasy": "mg", "malay": "ms", "malayalam": "ml", "maltese": "mt", "maori": "mi",
    "marathi": "mr", "mongolian": "mn", "nepali": "ne", "norwegian": "no", "nynorsk": "nn",
    "occitan": "oc", "odia": "or", "oriya": "or", "pashto": "ps", "persian": "fa", "farsi": "fa",
    "polish": "pl", "portuguese": "pt", "punjabi": "pa", "romanian": "ro", "russian": "ru",
    "sanskrit": "sa", "serbian": "sr", "shona": "sn", "sindhi": "sd", "sinhala": "si",
    "sinhalese": "si", "slovak": "sk", "slovenian": "sl", "somali": "so", "spanish": "es",
    "sundanese": "su", "swahili": "sw", "swedish": "sv", "tagalog": "tl", "filipino": "tl",
    "tajik": "tg", "tamil": "ta", "tatar": "tt", "telugu": "te", "thai": "th",
    "tibetan": "bo", "turkish": "tr", "turkmen": "tk", "ukrainian": "uk", "urdu": "ur",
    "uyghur": "ug", "uzbek": "uz", "vietnamese": "vi", "welsh": "cy", "yiddish": "yi",
    "yoruba": "yo", "zulu": "zu",
}


def iso_code_for_language(name_or_code: str | None) -> str | None:
    """Return the ISO 639-1 code Whisper expects. Accepts full names or 2-letter codes.
    Returns None for auto/blank so Whisper auto-detects."""
    if not name_or_code:
        return None
    v = name_or_code.strip().lower()
    if v in ("", "auto", "any", "detect"):
        return None
    # Direct ISO code (2-3 letters)
    if len(v) <= 3 and v.isalpha():
        return v
    return _ISO_MAP.get(v)


async def extract_from_url(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        r = await client.get(url, headers={"User-Agent": "AiPilluStudio/1.0 (Story-to-Film AI Agent; +https://aipillu.example) requests"})
        r.raise_for_status()
        html = r.text
    soup = BeautifulSoup(html, "lxml")
    # Remove scripts and styles
    for tag in soup(["script", "style", "noscript", "iframe", "nav", "footer", "header"]):
        tag.decompose()
    # Prefer article/main content
    root = soup.find("article") or soup.find("main") or soup.body or soup
    text = root.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:20000]


def extract_from_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n\n".join(parts).strip()[:40000]


def extract_from_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs).strip()[:40000]


def extract_from_txt(data: bytes) -> str:
    try:
        return data.decode("utf-8", errors="ignore").strip()[:40000]
    except Exception:
        return ""


async def extract_from_upload(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return extract_from_pdf(data)
    if name.endswith(".docx"):
        return extract_from_docx(data)
    if name.endswith(".doc"):
        # Best effort: try text extraction
        return extract_from_txt(data)
    if name.endswith(".txt") or name.endswith(".md"):
        return extract_from_txt(data)
    # Fallback: attempt text
    return extract_from_txt(data)


async def transcribe_audio(audio_path: str, language: str | None = None) -> str:
    """Transcribe audio file using OpenAI Whisper via emergentintegrations."""
    from emergentintegrations.llm.openai import OpenAISpeechToText
    stt = OpenAISpeechToText(api_key=os.getenv("EMERGENT_LLM_KEY"))
    with open(audio_path, "rb") as f:
        response = await stt.transcribe(
            file=f,
            model="whisper-1",
            response_format="json",
            language=language,
        )
    return response.text if hasattr(response, "text") else str(response)
