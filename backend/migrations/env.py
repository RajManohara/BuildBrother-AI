from alembic import context
from app.core.config import Settings
from app.database import Base, create_database
from app import models  # Register all domain metadata.

target_metadata = Base.metadata
database_url = context.config.attributes.get("database_url") or Settings().database_url

if context.is_offline_mode():
    context.configure(url=database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine, _ = create_database(database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
