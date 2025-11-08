# app/db/db.py
"""
Database connection module.

Provides:
 - connect_db(db_url=None): async connect and create tables if needed
 - disconnect_db(): async disconnect
 - get_database(): return databases.Database instance
 - get_metadata(): return SQLAlchemy MetaData (for table definitions)
"""
import logging
from typing import Optional
import sqlalchemy
from sqlalchemy import create_engine
from databases import Database
from app.config import get_settings

logger = logging.getLogger("conversational-ivr-poc.db")

settings = get_settings()

# Shared metadata used by db models
metadata = sqlalchemy.MetaData()

# Database instance (databases.Database)
_database: Optional[Database] = None


def _normalize_sqlite_url(url: str) -> (str, str):
    """
    Convert a DB URL into:
      - async_url for databases.Database (sqlite -> sqlite+aiosqlite)
      - sync_url for SQLAlchemy create_engine (sqlite+aiosqlite -> sqlite)
    """
    if not url:
        url = settings.DB_URL

    # If using sqlite and not aiosqlite, convert
    if url.startswith("sqlite:///") and "+aiosqlite" not in url:
        async_url = url.replace("sqlite:///", "sqlite+aiosqlite:///")
        sync_url = url
        return async_url, sync_url
    # If already aiosqlite
    if url.startswith("sqlite+aiosqlite:///"):
        async_url = url
        sync_url = url.replace("+aiosqlite", "")
        return async_url, sync_url
    # For other DBs, assume URL is fine for both (may need adjustments per DB)
    return url, url


async def connect_db(db_url: Optional[str] = None):
    """
    Connect the global Database instance and ensure tables are created.

    Usage: await connect_db()  # uses settings.DB_URL by default
    """
    global _database
    if db_url is None:
        db_url = settings.DB_URL

    async_url, sync_url = _normalize_sqlite_url(db_url)

    if _database and _database.is_connected:
        logger.debug("Database already connected")
        return _database

    _database = Database(async_url)
    logger.info("Connecting to database: %s", async_url)
    await _database.connect()

    # Create tables (synchronously) using SQLAlchemy engine against sync_url
    try:
        engine = create_engine(sync_url, connect_args={"check_same_thread": False} if sync_url.startswith("sqlite") else {})
        metadata.create_all(engine)
        logger.info("Ensured database tables are created (sync_url=%s)", sync_url)
    except Exception as exc:
        logger.exception("Failed to create tables: %s", exc)

    return _database


async def disconnect_db():
    """Disconnect the global Database instance if connected."""
    global _database
    if _database and _database.is_connected:
        logger.info("Disconnecting database")
        await _database.disconnect()
        _database = None


def get_database() -> Database:
    """Return Database instance (may be not connected yet)."""
    global _database
    if _database is None:
        # create instance but don't connect
        async_url, _ = _normalize_sqlite_url(settings.DB_URL)
        _database = Database(async_url)
    return _database


def get_metadata() -> sqlalchemy.MetaData:
    return metadata
