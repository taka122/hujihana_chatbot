import os
import uuid
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Document, Workspace

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/rag")
engine = create_engine(DATABASE_URL)

def check_status():
    with Session(engine) as session:
        workspaces = session.execute(select(Workspace)).scalars().all()
        print(f"Total Workspaces: {len(workspaces)}")
        for ws in workspaces:
            print(f"\nWorkspace: {ws.name} ({ws.id})")
            docs = session.execute(select(Document).filter(Document.workspace_id == ws.id)).scalars().all()
            print(f"Total Documents: {len(docs)}")
            stats = {}
            for d in docs:
                stats[d.status] = stats.get(d.status, 0) + 1
                if d.status == "failed":
                    print(f"  - [FAILED] {d.file_name}: {d.fail_reason}")
                elif d.status == "processing":
                    print(f"  - [PROCESSING] {d.file_name}")
            
            for status, count in stats.items():
                print(f"  {status}: {count}")

if __name__ == "__main__":
    check_status()
