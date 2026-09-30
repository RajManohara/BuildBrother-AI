"""One collector process per workspace. PostgreSQL advisory lock prevents overlap."""
import argparse
import logging
import time
from sqlalchemy import text
from app.core.config import Settings
from app.database import create_database
from app.github import collect

logger = logging.getLogger("buildbrother.collector")


def run_once(settings):
    engine, sessions = create_database(settings.database_url)
    try:
        with engine.connect() as lock_connection:
            postgres = engine.dialect.name == "postgresql"
            if postgres and not lock_connection.scalar(text("SELECT pg_try_advisory_lock(42719021)")):
                return {"status": "already_running"}
            try:
                with sessions() as session:
                    try:
                        result = collect(session, settings)
                        session.commit()
                        return result
                    except Exception:
                        session.commit()  # Persist safe cursor/backoff state for retry.
                        raise
            finally:
                if postgres:
                    lock_connection.execute(text("SELECT pg_advisory_unlock(42719021)"))
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    while True:
        try:
            result = run_once(settings)
            logger.info("Collection result: %s", result)
        except Exception as error:
            logger.error("Collection failed (%s). Check configuration and resource availability.", type(error).__name__)
            if args.once:
                raise SystemExit(1)
        if args.once:
            return
        time.sleep(settings.collector_interval_seconds)


if __name__ == "__main__":
    main()
