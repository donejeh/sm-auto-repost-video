"""Database session and base."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_jobs_slug() -> None:
    from sqlalchemy import inspect, or_, text

    from backend.db.models import Job
    from backend.services.slug import make_initial_slug, refresh_slug_from_title

    insp = inspect(engine)
    if "jobs" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("jobs")}
    if "slug" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN slug VARCHAR(128)"))

    db = SessionLocal()
    try:
        for job in db.query(Job).filter(or_(Job.slug.is_(None), Job.slug == "")).all():
            slug = make_initial_slug()
            if job.title:
                slug = refresh_slug_from_title(job.title, slug)
            while db.query(Job).filter(Job.slug == slug, Job.id != job.id).first():
                slug = make_initial_slug()
                if job.title:
                    slug = refresh_slug_from_title(job.title, slug)
            job.slug = slug
        db.commit()
    finally:
        db.close()


def init_db() -> None:
    from backend.db import models  # noqa: F401

    settings.storage_path.mkdir(parents=True, exist_ok=True)
    (settings.storage_path.parent / "data").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _migrate_jobs_slug()
