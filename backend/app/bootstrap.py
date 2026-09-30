"""Run versioned schema migrations before starting the API or collector."""
from pathlib import Path
from alembic import command
from alembic.config import Config


def migrate(database_url=None):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    if database_url:
        config.attributes["database_url"] = database_url
    command.upgrade(config, "head")


if __name__ == "__main__":
    migrate()
