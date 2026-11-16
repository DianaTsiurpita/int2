import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def read_secret(name: str) -> str:
    path = Path('/run/secrets') / name
    try:
        value = path.read_text(encoding='utf-8').strip()
    except OSError as exc:
        raise RuntimeError(f'Required secret {name} is unavailable at {path}') from exc
    if not value:
        raise RuntimeError(f'Required secret {name} is empty')
    return value


DATABASE_URL = URL.create(
    drivername='postgresql+psycopg',
    username=os.environ.get('POSTGRES_USER', 'orders'),
    password=read_secret('db_password'),
    host=os.environ.get('POSTGRES_HOST', 'postgres'),
    port=5432,
    database=os.environ.get('POSTGRES_DB', 'orders'),
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
