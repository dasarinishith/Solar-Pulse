"""
SolarPulse Database Connection & Engine Setup
Supports local SQLite with seamless fallback, or production PostgreSQL / Supabase.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from database.models import Base

def get_database_url() -> str:
    # 1. Check Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "SUPABASE_DB_URL" in st.secrets:
                return str(st.secrets["SUPABASE_DB_URL"])
            if "database" in st.secrets and "url" in st.secrets["database"]:
                return str(st.secrets["database"]["url"])
    except Exception:
        pass

    # 2. Check Environment Variables
    env_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if env_url:
        return env_url

    # 3. Default: Local SQLite
    database_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "solarpulse.db"))
    return f"sqlite:///{database_path}"

DATABASE_URL = get_database_url()

# Normalize PostgreSQL schema prefix for SQLAlchemy 2.0+
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )

SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(SessionFactory)

def init_db():
    """Initializes tables in the active database."""
    Base.metadata.create_all(bind=engine)

def get_db_session():
    """Context manager or getter for database sessions."""
    return Session()

