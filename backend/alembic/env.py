from logging.config import fileConfig

import os
from dotenv import load_dotenv

# Load .env first so DATABASE_URL is available
_env_file = os.environ.get("ENV_FILE", ".env.production")
load_dotenv(_env_file)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)

from sqlalchemy import engine_from_config, pool
from alembic import context

# Import Base and all models
from models import Base  # noqa: E402
import models  # noqa: E402  — ensures all model modules are imported

config = context.config

# Override sqlalchemy.url from environment
_database_url = os.getenv("DATABASE_URL", "sqlite:///./leads.db")
if "mysql" in _database_url and "pymysql" not in _database_url:
    _database_url = _database_url.replace("mysql://", "mysql+pymysql://")
config.set_main_option("sqlalchemy.url", _database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    return _database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
