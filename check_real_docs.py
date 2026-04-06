import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Document, IngestionRun

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/rag")
engine = create_engine(DATABASE_URL)

def check_status():
    with Session(engine) as session:
        docs = session.query(Document).all()
        for doc in docs:
            print(f"Document: {doc.file_name} ({doc.id}) status={doc.status}")
            runs = session.query(IngestionRun).filter(IngestionRun.document_id == doc.id).order_by(IngestionRun.started_at.desc()).all()
            for i, run in enumerate(runs):
                print(f"\nRun {i+1}: id={run.id} started_at={run.started_at} finished_at={run.finished_at}")
                print(f"Log: {run.log}")

if __name__ == "__main__":
    check_status()
