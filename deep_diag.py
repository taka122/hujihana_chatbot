import uuid
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from app.db import SessionLocal, engine
from app.models import Document, Workspace

def run():
    print(f"Engine URL: {engine.url}")
    
    with SessionLocal() as session:
        # Try raw SQL to see what happens
        res = session.execute(text("SELECT count(*) FROM documents")).scalar()
        print(f"Raw SQL count of documents: {res}")
        
        # Check actual columns in ORM
        docs = session.query(Document).all()
        print(f"ORM count of documents: {len(docs)}")
        
        if len(docs) == 0 and res > 0:
            print("ERROR: Raw SQL found rows but ORM found none!")
            # Check the table name of the model
            print(f"Model Table Name: {Document.__tablename__}")
            # Check for any filters (this is unusual in common SQLAlchemy but worth checking)
            # SQLAlchemy 2.0 uses select(Document)
            docs2 = session.execute(select(Document)).scalars().all()
            print(f"SQLAlchemy 2.0 select count: {len(docs2)}")

if __name__ == "__main__":
    run()
