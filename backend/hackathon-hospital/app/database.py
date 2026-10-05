from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(settings.DATABASE_URL)
else:
    # Per process: 5 + 10 connections. 4 API workers + 1 MCP process stay well below PostgreSQL's 100.
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,   # drop connections that died (e.g. after a PostgreSQL restart)
        pool_recycle=1800,
        pool_timeout=30,
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
