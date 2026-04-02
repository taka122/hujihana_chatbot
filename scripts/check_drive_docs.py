import os
from sqlalchemy import create_path
import sys

# プロジェクトのルートをPathに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models import Document
from app.db import SessionLocal

def check_docs():
    db = SessionLocal()
    try:
        docs = db.query(Document).all()
        print(f"Total documents: {len(docs)}")
        
        drive_docs = [d for d in docs if d.storage_key.startswith("drive://")]
        print(f"Google Drive documents: {len(drive_docs)}")
        
        for d in drive_docs:
            print(f" - {d.title} (Status: {d.ingestion_status}, Path: {d.storage_key})")
            
        if not drive_docs:
            print("No Google Drive documents found in DB.")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_docs()
