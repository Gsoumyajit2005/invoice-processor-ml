# src/database.py

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text
from typing import Generator, Optional
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Get credentials (with defaults to avoid immediate crashes if vars are missing)
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# 2. Construct DATABASE_URL conditionally
DATABASE_URL = None
engine = None
DB_CONNECTED = False  # Track actual connection status

if POSTGRES_USER and POSTGRES_PASSWORD and POSTGRES_DB:
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    try:
        # 3. Create the engine only if we have credentials
        engine = create_engine(DATABASE_URL, echo=False)
        
        # 4. Test actual connection (once at startup)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        DB_CONNECTED = True
        print("✅ Database connection verified.")
    except Exception as e:
        print(f"⚠️ Database unavailable: {e}")
        DB_CONNECTED = False
else:
    print("⚠️ Database credentials missing. Database features will be disabled.")

def init_db():
    """
    Idempotent DB initialization.
    Only runs if engine is successfully configured AND connected.
    """
    if engine and DB_CONNECTED:
        try:
            SQLModel.metadata.create_all(engine)
            print("✅ Database tables created/verified.")
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
    # Silent skip when DB is not connected - message already shown at startup

def get_session() -> Generator[Optional[Session], None, None]:
    """
    Dependency for yielding a database session.
    Yields None if database is not configured.
    """
    if engine:
        with Session(engine) as session:
            yield session
    else:
        # Yield None so code depending on this doesn't crash immediately,
        # but can check 'if session is None'.
        yield None