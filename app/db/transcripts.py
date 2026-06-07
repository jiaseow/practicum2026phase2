from __future__ import annotations

import json
from itertools import zip_longest
from typing import Any

import psycopg

from app.core.config import get_settings
from app.schemas.search import TranscriptSearchResult
from app.services.chunking import TextChunk


def store_transcript(
    *,
    project_id: str,
    transcript: str,
    duration: float | None,
    chunks: list[TextChunk],
    embeddings: list[list[float]],
    source: str = "whisper",
) -> bool:
    settings = get_settings()
    if not settings.database_url:
        return False

    try:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO transcripts (project_id, transcript, duration_seconds)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (project_id)
                    DO UPDATE SET transcript = EXCLUDED.transcript,
                                  duration_seconds = EXCLUDED.duration_seconds,
                                  created_at = now()
                    """,
                    (project_id, transcript, duration),
                )

                cursor.execute("DELETE FROM transcript_chunks WHERE project_id = %s", (project_id,))
                for chunk, embedding in zip_longest(chunks, embeddings):
                    if chunk is None or embedding is None:
                        raise ValueError("Chunk and embedding counts do not match.")
                    cursor.execute(
                        """
                        INSERT INTO transcript_chunks
                            (id, project_id, text, start_time, end_time, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            chunk.id,
                            project_id,
                            chunk.text,
                            chunk.start_time,
                            chunk.end_time,
                            _to_vector_literal(embedding),
                            json.dumps({"source": source}),
                        ),
                    )
            conn.commit()
            return True
    except psycopg.OperationalError:
        return False


def _to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"


def get_transcript_summary(project_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.database_url:
        return None

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT t.project_id,
                       t.duration_seconds,
                       t.created_at,
                       COUNT(c.id)::int AS chunk_count
                FROM transcripts t
                LEFT JOIN transcript_chunks c ON c.project_id = t.project_id
                WHERE t.project_id = %s
                GROUP BY t.project_id, t.duration_seconds, t.created_at
                """,
                (project_id,),
            )
            row = cursor.fetchone()

    if row is None:
        return None

    return {
        "project_id": row[0],
        "duration": row[1],
        "created_at": row[2],
        "chunk_count": row[3],
    }


def delete_transcript(project_id: str) -> bool:
    settings = get_settings()
    if not settings.database_url:
        return False

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM transcripts WHERE project_id = %s", (project_id,))
            deleted = cursor.rowcount > 0
        conn.commit()

    return deleted


def search_transcript_chunks(
    *,
    project_id: str,
    query_embedding: list[float],
    limit: int,
    similarity_threshold: float,
) -> list[TranscriptSearchResult]:
    settings = get_settings()
    if not settings.database_url:
        raise ValueError("DATABASE_URL is required to search stored transcript chunks.")

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id,
                       text,
                       start_time,
                       end_time,
                       metadata,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM transcript_chunks
                WHERE project_id = %s
                  AND 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    _to_vector_literal(query_embedding),
                    project_id,
                    _to_vector_literal(query_embedding),
                    similarity_threshold,
                    _to_vector_literal(query_embedding),
                    limit,
                ),
            )
            rows = cursor.fetchall()

    return [
        TranscriptSearchResult(
            id=row[0],
            text=row[1],
            startTime=float(row[2]),
            endTime=float(row[3]),
            metadata=row[4] or {},
            similarity=round(float(row[5]), 4),
        )
        for row in rows
    ]
