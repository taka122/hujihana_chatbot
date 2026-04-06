import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Document, IngestionRun

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/rag")
engine = create_engine(DATABASE_URL)

def print_detail():
    with Session(engine) as session:
        doc = session.query(Document).filter(Document.file_name == "朝の準備　アポ帳出し.MOV").first()
        if not doc:
            with open("/app/detail.txt", "w") as f:
                f.write("Document not found\n")
            return
        
        with open("/app/detail.txt", "w") as f:
            f.write(f"--- FAIL REASON ---\n")
            f.write(f"{doc.fail_reason}\n")
            f.write("-------------------\n")
            
            runs = session.query(IngestionRun).filter(IngestionRun.document_id == doc.id).order_by(IngestionRun.started_at.desc()).all()
            for i, run in enumerate(runs):
                f.write(f"\n--- RUN {i} LOG ---\n")
                f.write(f"{run.log}\n")

if __name__ == "__main__":
    print_detail()
