#!/usr/bin/env python3
"""
Initialize the Bee Monitoring databases.
- Creates the SQLAlchemy tables (e.g. `user`) via Flask app context
- Creates/ensures analytics tables via the bee_monitoring blueprint's initializer

This script mirrors the DB path resolution used by `api/main.py` so that
all components write to the same SQLite file.
"""

import os
import sys
import logging
from pathlib import Path

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure repository root is on sys.path so we can import `api.*`
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _resolve_db_path() -> str:
    # 1) Respect explicit env var if provided
    env_path = os.environ.get('BEE_DB_PATH')
    if env_path:
        os.makedirs(os.path.dirname(env_path), exist_ok=True)
        return env_path

    # 2) Preferred production/data path (aligns with systemd ReadWritePaths)
    prod_dir = "/opt/bee-monitoring/data"
    try:
        if os.path.isdir("/opt/bee-monitoring") and os.access("/opt/bee-monitoring", os.W_OK):
            os.makedirs(prod_dir, exist_ok=True)
            return os.path.join(prod_dir, 'bee_monitoring.db')
    except Exception:
        pass

    # 3) Fallback to local repo path for development
    local_dir = os.path.join(REPO_ROOT, 'api', 'database')
    os.makedirs(local_dir, exist_ok=True)
    return os.path.join(local_dir, 'bee_monitoring.db')


def init_sqlalchemy_tables(db_path: str) -> None:
    """Create SQLAlchemy-managed tables (e.g. `user`)."""
    from flask import Flask
    from api.models.user import db  # imports SQLAlchemy instance and models

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    with app.app_context():
        db.create_all()
        logger.info("SQLAlchemy tables created (user, ...)")


def init_bee_tables() -> None:
    """Create analytics/monitoring tables by importing the blueprint module.

    Importing `api.routes.bee_monitoring` will call its `init_bee_database()`
    at import time using the DB path in BEE_DB_PATH.
    """
    import importlib

    importlib.import_module('api.routes.bee_monitoring')
    logger.info("Bee monitoring tables initialized (activity_metrics, behavior_analysis, health_assessment, environmental_data, alerts, system_status)")


def main() -> int:
    try:
        db_path = _resolve_db_path()
        os.environ['BEE_DB_PATH'] = db_path
        logger.info(f"Initializing database at: {db_path}")

        init_sqlalchemy_tables(db_path)
        init_bee_tables()

        logger.info("Database initialization completed successfully")
        return 0
    except Exception as e:
        logger.exception(f"Database initialization failed: {e}")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
