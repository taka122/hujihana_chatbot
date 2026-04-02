import uuid
import json
from app.db import SessionLocal
from app.models import Document, DocumentStatus, Workspace
from app.services.queue import enqueue_ingestion
from app.config import get_settings

def import_single_file(file_id, file_name, mime_type):
    db = SessionLocal()
    try:
        workspace = db.query(Workspace).first()
        if not workspace:
            print("No workspace found")
            return
            
        storage_key = f"drive://{file_id}"
        existing = db.query(Document).filter(Document.storage_key == storage_key).first()
        if existing:
            print(f"Already exists: {file_name}")
            doc_id = existing.id
        else:
            doc_id = uuid.uuid4()
            doc = Document(
                id=doc_id,
                workspace_id=workspace.id,
                file_name=file_name,
                mime_type=mime_type,
                storage_key=storage_key,
                status=DocumentStatus.processing,
                tags=["google-drive", "test-small"],
            )
            db.add(doc)
            db.commit()
            print(f"Created document: {file_name}")
            
        enqueue_ingestion(str(doc_id))
        print(f"Enqueued ingestion for: {file_name}")
    finally:
        db.close()

if __name__ == "__main__":
    # Smallest video identified:
    import_single_file(
        "1JDSGLGb-03B6KmqtNnVpGLHaZeEt", 
        "朝の準備　アポ帳出し", 
        "video/quicktime"
    )
