from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from app.bootstrap import migrate
from app.database import create_database


def test_upgrade_downgrade_upgrade(tmp_path):
    url="sqlite:///"+str(tmp_path/"migrations.db")
    config=Config("alembic.ini")
    config.attributes["database_url"]=url
    migrate(url)
    engine,_=create_database(url)
    assert {"deployments","runtime_events","incident_evidence","collector_cursors"} <= set(inspect(engine).get_table_names())
    engine.dispose()
    command.downgrade(config,"base")
    migrate(url)
