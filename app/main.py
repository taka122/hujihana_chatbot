from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.logging import setup_logging
from app.routers import chat, documents, workspaces

setup_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspaces.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs", status_code=307)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
