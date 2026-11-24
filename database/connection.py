"""
SolarPulse Database Connection & Engine Setup
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from database.models import Base

DATABASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "solarpulse.db"))
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(SessionFactory)

def init_db():
    """Initializes tables in the SQLite database."""
    Base.metadata.create_all(bind=engine)

def get_db_session():
    """Context manager or getter for database sessions."""
    return Session()
