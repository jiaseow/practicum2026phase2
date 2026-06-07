CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS transcripts (
    project_id TEXT PRIMARY KEY,
    transcript TEXT NOT NULL,
    duration_seconds DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transcript_chunks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES transcripts(project_id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    start_time DOUBLE PRECISION NOT NULL DEFAULT 0,
    end_time DOUBLE PRECISION NOT NULL DEFAULT 0,
    embedding vector(1536) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS transcript_chunks_project_id_idx
    ON transcript_chunks(project_id);

CREATE INDEX IF NOT EXISTS transcript_chunks_embedding_cosine_idx
    ON transcript_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
