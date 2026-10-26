from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db(target_engine=engine):
    """Creates tables and performs safe, additive column migrations if needed."""
    Base.metadata.create_all(bind=target_engine)
    inspector = inspect(target_engine)
    existing_tables = inspector.get_table_names()
    with target_engine.connect() as conn:
        for table in ["applications", "roadmap_snapshots", "interview_sessions", "resume_analyses"]:
            if table in existing_tables:
                col_names = [c["name"] for c in inspector.get_columns(table)]
                if "user_id" not in col_names:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                    conn.commit()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

