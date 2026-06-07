from __future__ import annotations

from pathlib import Path

from openai import APIError, APIStatusError, AuthenticationError, AsyncOpenAI

from app.core.config import get_settings
from app.services.chunking import TranscriptSegment


def get_openai_client() -> AsyncOpenAI:
    settings = get_settings()
    if not settings.openai_api_key or "replace-me" in settings.openai_api_key:
        raise ValueError("Set a valid OPENAI_API_KEY in .env before transcribing or embedding transcript content.")
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def transcribe_audio(audio_path: Path) -> tuple[str, float | None, list[TranscriptSegment]]:
    settings = get_settings()
    client = get_openai_client()

    try:
        with audio_path.open("rb") as audio_file:
            result = await client.audio.transcriptions.create(
                model=settings.whisper_model,
                file=audio_file,
                response_format="verbose_json",
            )
    except AuthenticationError as exc:
        raise ValueError("OpenAI authentication failed. Check OPENAI_API_KEY in .env and restart the API server.") from exc
    except (APIStatusError, APIError) as exc:
        raise ValueError(f"OpenAI transcription request failed: {exc}") from exc

    transcript = getattr(result, "text", "") or ""
    duration = getattr(result, "duration", None)
    raw_segments = getattr(result, "segments", None) or []
    segments = [
        TranscriptSegment(
            text=getattr(segment, "text", "") or "",
            start_time=float(getattr(segment, "start", 0) or 0),
            end_time=float(getattr(segment, "end", 0) or 0),
        )
        for segment in raw_segments
        if getattr(segment, "text", "")
    ]
    return transcript.strip(), duration, segments


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()
    client = get_openai_client()
    try:
        result = await client.embeddings.create(model=settings.embedding_model, input=texts)
    except AuthenticationError as exc:
        raise ValueError("OpenAI authentication failed. Check OPENAI_API_KEY in .env and restart the API server.") from exc
    except (APIStatusError, APIError) as exc:
        raise ValueError(f"OpenAI embedding request failed: {exc}") from exc
    return [item.embedding for item in result.data]
