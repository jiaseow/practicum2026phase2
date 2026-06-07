from __future__ import annotations

from app.core.config import get_settings
from app.db.transcripts import search_transcript_chunks
from app.schemas.search import SearchRequest, SearchResponse
from app.services.openai_client import embed_texts


async def search_transcript(request: SearchRequest) -> SearchResponse:
    query = request.query.strip()
    if not query:
        raise ValueError("query is required.")

    embeddings = await embed_texts([query])
    results = search_transcript_chunks(
        project_id=request.project_id,
        query_embedding=embeddings[0],
        limit=request.limit,
        similarity_threshold=request.similarity_threshold,
    )
    return SearchResponse(
        projectId=request.project_id,
        query=query,
        results=results,
        resultCount=len(results),
        embeddingModel=get_settings().embedding_model,
    )
