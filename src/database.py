# src/database.py

from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os

# --- INSTRUCTIONS ---
# 1. Get credentials from environment variables (Os.getenv)
# 2. Construct the DATABASE_URL string: postgresql://user:pass@host:port/db
# 3. Create the SQLModel engine
# 4. Implement the init_db and get_session functions

# TODO: Define constants for DB params (POSTGRES_USER, etc.)

# TODO: Define DATABASE_URL

# TODO: Create 'engine' using create_engine(DATABASE_URL)

def init_db():
    """
    Idempotent DB initialization.
    Should create all tables defined in SQLModel metadata.
    """
    # TODO: Call SQLModel.metadata.create_all(engine)
    pass

def get_session() -> Generator[Session, None, None]:
    """
    Dependency for yielding a database session.
    Useful for FastAPI dependencies or context usage.
    """
    # TODO: Open a session with the engine, yield it, and ensure it closes
    pass
