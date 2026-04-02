from app.db import SessionLocal
from app.models import Document, DocumentStatus
import uuid

db = SessionLocal()
try:
    failed_docs = db.query(Document).filter(Document.status == DocumentStatus.failed).all()
    for doc in failed_docs:
        print(f"Resetting document: {doc.file_name} ({doc.id})")
        doc.status = DocumentStatus.processing
        doc.fail_reason = None
        # We don't trigger BackgroundTasks here easily via a script without running the app.
        # But wait, we can't easily re-trigger BackgroundTasks from a standalone script without the FastAPI app context.
    db.commit()
    print(f"Reset {len(failed_docs)} documents. Please re-upload or I will provide a way to re-trigger.")
finally:
    db.close()
