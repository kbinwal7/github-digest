from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import get_settings
from app.services.github import GitHubClient
from app.services.vector_store import IssueVectorStore
from app.services.rag import ContributionRAGEngine
from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings=get_settings()
    app.state.settings=settings
    app.state.github=GitHubClient(settings.github_token)
    app.state.vector_store=None
    app.state.rag=None
    if settings.gemini_api_key and settings.qdrant_url:
        try:
            app.state.vector_store=IssueVectorStore(settings)
            app.state.rag=ContributionRAGEngine(settings)
        except Exception as exc:
            app.state.rag_error=str(exc)
    yield
    if app.state.vector_store:
        app.state.vector_store.qdrant.close()

app=FastAPI(title="GitHub Digest API",version="2.0.0",lifespan=lifespan)
app.include_router(router)
app.mount("/static",StaticFiles(directory="app/static"),name="static")

@app.get("/health")
async def health():
    return {"status":"ok"}

@app.get("/")
async def index():
    return FileResponse("app/static/index.html")
