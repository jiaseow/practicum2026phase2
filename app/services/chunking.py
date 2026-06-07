from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    id: str
    text: str
    start_time: float
    end_time: float


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start_time: float
    end_time: float


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text.split()) * 1.3))


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def chunk_transcript(
    transcript: str,
    *,
    project_id: str,
    duration: float | None,
    target_tokens: int,
    overlap_tokens: int,
) -> list[TextChunk]:
    sentences = split_sentences(transcript)
    if not sentences:
        return []

    chunks: list[TextChunk] = []
    current: list[str] = []
    current_tokens = 0
    total_tokens = sum(estimate_tokens(sentence) for sentence in sentences)
    seconds_per_token = (duration or 0) / total_tokens if duration and total_tokens else 0
    cursor_tokens = 0

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)
        if current and current_tokens + sentence_tokens > target_tokens:
            chunks.append(
                _build_chunk(
                    project_id=project_id,
                    index=len(chunks),
                    sentences=current,
                    start_token=cursor_tokens,
                    token_count=current_tokens,
                    seconds_per_token=seconds_per_token,
                )
            )
            overlap = _take_overlap(current, overlap_tokens)
            cursor_tokens += max(0, current_tokens - sum(estimate_tokens(item) for item in overlap))
            current = overlap
            current_tokens = sum(estimate_tokens(item) for item in current)

        current.append(sentence)
        current_tokens += sentence_tokens

    if current:
        chunks.append(
            _build_chunk(
                project_id=project_id,
                index=len(chunks),
                sentences=current,
                start_token=cursor_tokens,
                token_count=current_tokens,
                seconds_per_token=seconds_per_token,
            )
        )

    return chunks


def chunk_transcript_segments(
    segments: list[TranscriptSegment],
    *,
    project_id: str,
    target_tokens: int,
    overlap_tokens: int,
) -> list[TextChunk]:
    if not segments:
        return []

    chunks: list[TextChunk] = []
    current: list[TranscriptSegment] = []
    current_tokens = 0

    for segment in segments:
        segment_tokens = estimate_tokens(segment.text)
        if current and current_tokens + segment_tokens > target_tokens:
            chunks.append(_build_segment_chunk(project_id, len(chunks), current))
            overlap = _take_segment_overlap(current, overlap_tokens)
            current = overlap
            current_tokens = sum(estimate_tokens(item.text) for item in current)

        current.append(segment)
        current_tokens += segment_tokens

    if current:
        chunks.append(_build_segment_chunk(project_id, len(chunks), current))

    return chunks


def _take_overlap(sentences: list[str], overlap_tokens: int) -> list[str]:
    overlap: list[str] = []
    total = 0
    for sentence in reversed(sentences):
        sentence_tokens = estimate_tokens(sentence)
        if overlap and total + sentence_tokens > overlap_tokens:
            break
        overlap.insert(0, sentence)
        total += sentence_tokens
    return overlap


def _take_segment_overlap(
    segments: list[TranscriptSegment], overlap_tokens: int
) -> list[TranscriptSegment]:
    overlap: list[TranscriptSegment] = []
    total = 0
    for segment in reversed(segments):
        segment_tokens = estimate_tokens(segment.text)
        if overlap and total + segment_tokens > overlap_tokens:
            break
        overlap.insert(0, segment)
        total += segment_tokens
    return overlap


def _build_segment_chunk(
    project_id: str, index: int, segments: list[TranscriptSegment]
) -> TextChunk:
    return TextChunk(
        id=f"{project_id}-chunk-{index + 1}",
        text=" ".join(segment.text.strip() for segment in segments if segment.text.strip()),
        start_time=round(segments[0].start_time, 2),
        end_time=round(segments[-1].end_time, 2),
    )


def _build_chunk(
    *,
    project_id: str,
    index: int,
    sentences: list[str],
    start_token: int,
    token_count: int,
    seconds_per_token: float,
) -> TextChunk:
    start_time = start_token * seconds_per_token
    end_time = (start_token + token_count) * seconds_per_token
    return TextChunk(
        id=f"{project_id}-chunk-{index + 1}",
        text=" ".join(sentences),
        start_time=round(start_time, 2),
        end_time=round(end_time, 2),
    )
