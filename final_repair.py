import uuid
from app.db import SessionLocal
from app.models import Document, DocumentStatus
from app.services.queue import enqueue_ingestion

def run():
    target_id_str = "8fc9580e-a20d-4c56-8367-e9a9d7010e9f"
    with SessionLocal() as session:
        doc = session.query(Document).filter(Document.id == target_id_str).first()
        if not doc:
            print(f"Target document {target_id_str} not found.")
            # List all for debugging
            all_docs = session.query(Document).all()
            for d in all_docs:
                print(f"  - Exist: {d.id} | {d.file_name}")
            return

        print(f"Found! Resetting status for: {doc.file_name}")
        doc.status = DocumentStatus.processing
        doc.fail_reason = None
        session.add(doc)
        session.commit()
        
        job_id = enqueue_ingestion(str(doc.id))
        print(f"Enqueued Ingestion Job: {job_id}")

if __name__ == "__main__":
    run()
