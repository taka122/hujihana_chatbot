import uuid
from app.db import SessionLocal, engine
from app.models import Document, DocumentStatus
from app.services.queue import enqueue_ingestion
from sqlalchemy import inspect

def run():
    print(f"Engine URL: {engine.url}")
    inspector = inspect(engine)
    print(f"Tables in DB: {inspector.get_table_names()}")
    
    db = SessionLocal()
    try:
        docs = db.query(Document).all()
        print(f"Total documents found via SQLAlchemy: {len(docs)}")
        for d in docs:
            print(f"  - {d.id} | {d.file_name}")
            
        target_id_str = "8fc9580e-a20d-4c56-8367-e9a9d7010e9f"
        target_doc = db.query(Document).filter(Document.id == target_id_str).first()
        
        if target_doc:
            print(f"Found! Resetting status for: {target_doc.file_name}")
            target_doc.status = DocumentStatus.processing
            target_doc.fail_reason = None
            db.add(target_doc)
            db.commit()
            job_id = enqueue_ingestion(str(target_doc.id))
            print(f"Enqueued Ingestion Job: {job_id}")
        else:
            print(f"Target ID {target_id_str} still not found via direct filter")
    finally:
        db.close()

if __name__ == "__main__":
    run()
