# from logging.config import fileConfig

# from sqlalchemy import engine_from_config
# from sqlalchemy import pool

# from alembic import context

# # this is the Alembic Config object, which provides
# # access to the values within the .ini file in use.
# config = context.config

# # Interpret the config file for Python logging.
# # This line sets up loggers basically.
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

# # add your model's MetaData object here
# # for 'autogenerate' support
# # from myapp import mymodel
# # target_metadata = mymodel.Base.metadata
# target_metadata = None

# # other values from the config, defined by the needs of env.py,
# # can be acquired:
# # my_important_option = config.get_main_option("my_important_option")
# # ... etc.


# def run_migrations_offline() -> None:
#     """Run migrations in 'offline' mode.

#     This configures the context with just a URL
#     and not an Engine, though an Engine is acceptable
#     here as well.  By skipping the Engine creation
#     we don't even need a DBAPI to be available.

#     Calls to context.execute() here emit the given string to the
#     script output.

#     """
#     url = config.get_main_option("sqlalchemy.url")
#     context.configure(
#         url=url,
#         target_metadata=target_metadata,
#         literal_binds=True,
#         dialect_opts={"paramstyle": "named"},
#     )

#     with context.begin_transaction():
#         context.run_migrations()


# def run_migrations_online() -> None:
#     """Run migrations in 'online' mode.

#     In this scenario we need to create an Engine
#     and associate a connection with the context.

#     """
#     connectable = engine_from_config(
#         config.get_section(config.config_ini_section, {}),
#         prefix="sqlalchemy.",
#         poolclass=pool.NullPool,
#     )

#     with connectable.connect() as connection:
#         context.configure(
#             connection=connection, target_metadata=target_metadata
#         )

#         with context.begin_transaction():
#             context.run_migrations()


# if context.is_offline_mode():
#     run_migrations_offline()
# else:
#     run_migrations_online()
# from logging.config import fileConfig
# import sys
# import os

# from sqlalchemy import engine_from_config, pool
# from alembic import context

# # Add src folder to sys.path so Alembic can import models
# sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

# # Import your Base from your database module
# from src.core.database import Base  # make sure Base.metadata includes all models
# # Import all models so that metadata is populated (important for autogenerate)
# import src.models

# # this is the Alembic Config object, which provides access to values within the .ini file in use.
# config = context.config

# # Setup logging from the config file
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

# # Metadata for 'autogenerate'
# target_metadata = Base.metadata

# def run_migrations_offline() -> None:
#     """Run migrations in 'offline' mode."""
#     url = config.get_main_option("sqlalchemy.url")
#     context.configure(
#         url=url,
#         target_metadata=target_metadata,
#         literal_binds=True,
#         dialect_opts={"paramstyle": "named"},
#     )

#     with context.begin_transaction():
#         context.run_migrations()


# def run_migrations_online() -> None:
#     """Run migrations in 'online' mode."""
#     connectable = engine_from_config(
#         config.get_section(config.config_ini_section),
#         prefix="sqlalchemy.",
#         poolclass=pool.NullPool,
#     )

#     with connectable.connect() as connection:
#         context.configure(connection=connection, target_metadata=target_metadata)

#         with context.begin_transaction():
#             context.run_migrations()


# if context.is_offline_mode():
#     run_migrations_offline()
# else:
#     run_migrations_online()
# from logging.config import fileConfig
# import sys
# import os

# from sqlalchemy import engine_from_config, pool
# from alembic import context

# # ---------------------------
# # Make sure src is importable
# # ---------------------------
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# # ---------------------------
# # Import your Base and models
# # ---------------------------
# from src.core.database import Base  # Base.metadata must include all models
# # Import all models to populate metadata
# import src.models.users
# import src.models.employee
# import src.models.clients
# import src.models.ecommerce
# import src.models.accounts
# import src.models.catalog
# import src.models.id
# import src.models.inventory
# import src.models.locations
# import src.models.partner_company
# import src.models.pos
# import src.models.procurement
# import src.models.providers
# import src.models.security
# import src.models.taxes

# # ---------------------------
# # Alembic config
# # ---------------------------
# config = context.config

# # Setup logging
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

# # Autogenerate support
# target_metadata = Base.metadata

# # ---------------------------
# # Offline migrations
# # ---------------------------
# def run_migrations_offline() -> None:
#     """Run migrations in 'offline' mode."""
#     url = config.get_main_option("sqlalchemy.url")
#     context.configure(
#         url=url,
#         target_metadata=target_metadata,
#         literal_binds=True,
#         dialect_opts={"paramstyle": "named"},
#     )

#     with context.begin_transaction():
#         context.run_migrations()


# # ---------------------------
# # Online migrations
# # ---------------------------
# def run_migrations_online() -> None:
#     """Run migrations in 'online' mode."""
#     # engine_from_config expects the section to include sqlalchemy.url
#     connectable = engine_from_config(
#         config.get_section(config.config_ini_section),  # normally [alembic]
#         prefix="sqlalchemy.",
#         poolclass=pool.NullPool,
#     )

#     with connectable.connect() as connection:
#         context.configure(connection=connection, target_metadata=target_metadata)

#         with context.begin_transaction():
#             context.run_migrations()


# # ---------------------------
# # Run migrations
# # ---------------------------
# if context.is_offline_mode():
#     run_migrations_offline()
# else:
#     run_migrations_online()
from logging.config import fileConfig
from alembic import context
from sqlalchemy import pool
import sys
from pathlib import Path


# --- Add project root to Python path ---
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

# --- Import your DB Base + engine ---
from src.core.database import Base, engine
import src.models  # Ensure all models are imported

# --- Alembic config ---
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for 'autogenerate'
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
