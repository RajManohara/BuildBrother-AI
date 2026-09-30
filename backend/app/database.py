from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Shared declarative base for BuildBrother's evidence model."""


def create_database(url: str):
    options = {"connect_timeout": 3} if url.startswith("postgresql") else {"check_same_thread": False}
    extra = {"poolclass": StaticPool} if url in ("sqlite://", "sqlite:///:memory:") else {}
    engine = create_engine(url, pool_pre_ping=True, connect_args=options, **extra)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enforce_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
