import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.extensions import db

# Ensure all models are registered on db.metadata before autogenerate compares.
from app.infrastructure import database as _database  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = db.metadata


def _get_engine():
    # Prefer the Flask app's bound engine (used when create_app auto-migrates
    # inside an app context); fall back to the ini sqlalchemy.url otherwise
    # (used by the `alembic` CLI for autogenerate/revision).
    try:
        from flask import current_app

        _ = current_app.config["SQLALCHEMY_DATABASE_URI"]
        return db.engine
    except Exception:
        return engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = _get_engine()
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()