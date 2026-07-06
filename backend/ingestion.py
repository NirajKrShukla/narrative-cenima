"""Ingestion utilities: parse PDF/DOCX/TXT files, URLs, and voice via Whisper."""
from __future__ import annotations
import io
import os
import re
import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document


async def extract_from_url(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 StoryFilmAgent"})
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
