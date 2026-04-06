from __future__ import annotations

from fastapi import FastAPI, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.logging import setup_logging
from app.routers import chat, documents, workspaces
from app.dependencies import verify_clinic_key

setup_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    dependencies=[Depends(verify_clinic_key)] if settings.clinic_password else []
)

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


@app.post("/import-drive")
async def import_drive_shortcut(
    folder_id: str = Body(..., embed=True),
):
    from app.db import SessionLocal
    from app.models import Workspace
    from app.services.queue import enqueue_drive_import
    from app.config import get_settings
    from fastapi import HTTPException
    
    db = SessionLocal()
    settings = get_settings()
    try:
        # 最初のワークスペースを使用
        workspace = db.query(Workspace).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="No workspace found")
            
        job_id = enqueue_drive_import(str(workspace.id), folder_id, gemini_api_key=settings.gemini_api_key)
        return {"job_id": job_id, "workspace_id": workspace.id, "status": "enqueued"}
    finally:
        db.close()
