from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import models here so they're registered on Base before create_all runs
    from app.models import document, audit, review  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_tenant_columns()


def _migrate_tenant_columns():
    """Backfill tenant columns for databases created before multi-tenancy."""
    legacy_tenant = settings.legacy_tenant_id.replace("'", "''")
    with engine.begin() as connection:
        inspector = inspect(connection)
        for table in ("documents", "evidence_packs", "audit_logs"):
            columns = {column["name"] for column in inspector.get_columns(table)}
            if "tenant_id" not in columns:
                connection.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN tenant_id VARCHAR NOT NULL DEFAULT '{legacy_tenant}'"
                ))
            connection.execute(text(
                f"CREATE INDEX IF NOT EXISTS ix_{table}_tenant_id ON {table} (tenant_id)"
            ))
