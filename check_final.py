import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Document, IngestionRun

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/rag")
engine = create_engine(DATABASE_URL)

def check_status():
    with Session(engine) as session:
        doc = session.query(Document).filter(Document.file_name == "20250324_朝の準備.mp4").first()
        if not doc:
            print("Document not found")
            return
        
        print(f"Status for {doc.file_name}: {doc.status}")
        if doc.fail_reason:
             print(f"Fail Reason: {doc.fail_reason}")
             
        run = session.query(IngestionRun).filter(IngestionRun.document_id == doc.id).order_by(IngestionRun.started_at.desc()).first()
        if run:
            print(f"Latest Run Log: {run.log}")

if __name__ == "__main__":
    check_status()
