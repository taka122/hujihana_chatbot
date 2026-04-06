import uuid
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Document, DocumentStatus
from app.services.queue import enqueue_ingestion

def retry_ingestion(doc_id_str):
    with SessionLocal() as session:
        # Use cast or string filtering to be safe
        doc = session.query(Document).filter(Document.id == doc_id_str).first()
        if not doc:
            print(f"Document {doc_id_str} not found in DB")
            return
        
        print(f"Retrying Ingestion for: {doc.file_name} ({doc.id})")
        doc.status = DocumentStatus.processing
        doc.fail_reason = None
        session.add(doc)
        session.commit()
        
        # Access settings for the API key if needed, but enqueue_ingestion handles it from env if not provided.
        job_id = enqueue_ingestion(str(doc.id))
        print(f"Enqueued job: {job_id}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        retry_ingestion(sys.argv[1])
    else:
        # Specific ID for 朝の準備　アポ帳出し.MOV
        retry_ingestion("8fc9580e-a20d-4c56-a7ab-f238f30669e6")
