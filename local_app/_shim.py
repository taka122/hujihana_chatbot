"""Shim module for local app.

Injects lightweight stub modules into ``sys.modules`` so that
``app.services.answer.AnswerService`` can be imported without
PostgreSQL / pgvector / redis being installed.

Import this module *before* any ``app.*`` imports in the local app.
"""
from __future__ import annotations

import sys
import types
import uuid
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Define a local RetrievedChunk that mirrors the real dataclass
# ---------------------------------------------------------------------------

@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    file_name: str
    ref_type: str
    ref: str
    snippet: str
    text: str
    page_start: int | None
    page_end: int | None
    section_title: str | None
    score: float
    raw_score: float


# ---------------------------------------------------------------------------
# Stub out the modules that need pgvector / sqlalchemy / redis / boto3
# ---------------------------------------------------------------------------

def _make_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def install() -> None:
    """Inject stubs into sys.modules.  Safe to call multiple times."""
    if "app.services.retrieve" in sys.modules:
        return  # Already patched or already imported — leave as-is.

    # Stub out lower-level packages that pgvector / psycopg pull in.
    for pkg in (
        "pgvector",
        "pgvector.sqlalchemy",
        "psycopg",
        "psycopg.binary",
        "redis",
        "rq",
        "boto3",
        "botocore",
        "botocore.client",
        "botocore.exceptions",
    ):
        if pkg not in sys.modules:
            _make_module(pkg)

    # Stub out app.models (imports pgvector.sqlalchemy.Vector)
    if "app.models" not in sys.modules:
        _make_module(
            "app.models",
            Chunk=None,
            Document=None,
            DocumentStatus=None,
            Workspace=None,
            IngestionRun=None,
        )

    # Stub out app.db
    if "app.db" not in sys.modules:
        _make_module("app.db", Base=None, get_db=lambda: None)

    # Provide real RetrievedChunk in app.services.retrieve stub
    _make_module(
        "app.services.retrieve",
        RetrievedChunk=RetrievedChunk,
        hybrid_retrieve=None,
    )


# Run on import
install()
