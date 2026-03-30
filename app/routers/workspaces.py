from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Document, Workspace
from app.schemas import WorkspaceCreate, WorkspaceResponse
from app.services.storage import StorageService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(db: Session = Depends(get_db)) -> list[Workspace]:
    stmt = select(Workspace).order_by(Workspace.created_at.desc())
    return list(db.scalars(stmt).all())


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db)) -> Workspace:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    workspace = Workspace(name=name)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@router.delete("/{wid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(wid: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    workspace = db.get(Workspace, wid)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    storage_keys = list(
        db.scalars(select(Document.storage_key).where(Document.workspace_id == wid)).all()
    )
    storage = StorageService()

    for key in storage_keys:
        try:
            storage.delete_object(key)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to delete object from storage during workspace deletion")
            raise HTTPException(status_code=503, detail=f"Storage unavailable: {exc}") from exc

    db.delete(workspace)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
