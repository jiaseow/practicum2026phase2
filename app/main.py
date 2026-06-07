from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.analyze_repo import router as analyze_repo_router
from app.api.agents import router as agents_router
from app.api.default_inputs import router as default_inputs_router
from app.api.evaluate import router as evaluate_router
from app.api.extract_claims import router as extract_claims_router
from app.api.projects import router as projects_router
from app.api.report import router as report_router
from app.api.search import router as search_router
from app.api.technologies import router as technologies_router
from app.api.transcribe import router as transcribe_router
from app.api.upload import router as upload_router
from app.api.verify import router as verify_router


app = FastAPI(
    title="AI Project Evaluation System",
    version="0.1.0",
    description="Prototype API for evaluating project submissions.",
)

app.include_router(transcribe_router, prefix="/api", tags=["transcription"])
app.include_router(analyze_repo_router, prefix="/api", tags=["repository analysis"])
app.include_router(agents_router, prefix="/api", tags=["agent pipeline"])
app.include_router(default_inputs_router, prefix="/api", tags=["default inputs"])
app.include_router(extract_claims_router, prefix="/api", tags=["claim extraction"])
app.include_router(verify_router, prefix="/api", tags=["claim verification"])
app.include_router(report_router, prefix="/api", tags=["reporting"])
app.include_router(search_router, prefix="/api", tags=["transcript search"])
app.include_router(evaluate_router, prefix="/api", tags=["evaluation pipeline"])
app.include_router(upload_router, prefix="/api", tags=["uploads"])
app.include_router(technologies_router, prefix="/api", tags=["technologies"])
app.include_router(projects_router, prefix="/api", tags=["projects"])
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def ui() -> FileResponse:
    return FileResponse(Path("static") / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
