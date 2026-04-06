import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Document, IngestionRun

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/rag")
engine = create_engine(DATABASE_URL)

def list_all_docs():
    with Session(engine) as session:
        docs = session.execute(select(Document)).scalars().all()
        for d in docs:
            print(f"ID: {d.id} | Name: {d.file_name} | Status: {d.status}")

if __name__ == "__main__":
    list_all_docs()
