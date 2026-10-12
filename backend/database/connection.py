from sqlalchemy import create_engine, text
from backend.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    pool_size=5,
    max_overflow=10,
)


def get_connection():
    return engine.connect()


def ping_database() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
