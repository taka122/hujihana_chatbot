import os
import uuid
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Document, IngestionRun

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/rag")
engine = create_engine(DATABASE_URL)

def check_run_details(doc_id_str):
    with Session(engine) as session:
        print(f"Searching for Document ID: {doc_id_str}")
        doc_id = uuid.UUID(doc_id_str)
        
        # List all documents for debugging
        all_docs = session.execute(select(Document)).scalars().all()
        print(f"Total documents in DB: {len(all_docs)}")
        for d in all_docs:
            print(f"  - {d.id} ({type(d.id)}) | {d.file_name}")
            if str(d.id) == doc_id_str:
                print("    MATCH FOUND!")
                doc = d
                break
        else:
            print("    NO MATCH FOUND IN LOOP")
            return

        print(f"Document: {doc.file_name} ({doc.id}) status={doc.status}")
        runs = session.execute(select(IngestionRun).filter(IngestionRun.document_id == doc.id).order_by(IngestionRun.started_at.desc())).scalars().all()
        print(f"Total runs found: {len(runs)}")
        for i, run in enumerate(runs):
            print(f"\nRun {i+1}: id={run.id} started_at={run.started_at} finished_at={run.finished_at}")
            print(f"Log: {run.log}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        check_run_details(sys.argv[1])
    else:
        print("Usage: python check_run_details.py <doc_id>")
