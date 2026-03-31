import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import os

# Get DB URL from env if possible, else use default
db_url = "postgresql+psycopg://postgres:postgres@localhost:5432/rag"

engine = create_engine(db_url)
with Session(engine) as session:
    from sqlalchemy import text
    result = session.execute(text("SELECT id, file_name, status, fail_reason FROM documents ORDER BY created_at DESC LIMIT 5"))
    for row in result:
        print(f"ID: {row.id}, File: {row.file_name}, Status: {row.status}, Fail Reason: {row.fail_reason}")
