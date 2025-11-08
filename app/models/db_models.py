# app/models/db_models.py
"""
SQLAlchemy table definitions for transcripts and flows (and optional sessions).
The module imports the shared `metadata` from app.db.db so `connect_db()` can create tables.
"""
import sqlalchemy as sa
from app.db.db import get_metadata

metadata = get_metadata()

# Transcripts table
transcripts = sa.Table(
    "transcripts",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("call_id", sa.String(length=128), index=True, nullable=False),
    sa.Column("timestamp", sa.String(length=64), nullable=True),
    sa.Column("text", sa.Text, nullable=False),
    sa.Column("source", sa.String(length=64), nullable=True),
    sa.Column("created_at", sa.String(length=64), nullable=True),
)

# Flows table
flows = sa.Table(
    "flows",
    metadata,
    sa.Column("flow_id", sa.String(length=128), primary_key=True),
    sa.Column("name", sa.String(length=256), nullable=True),
    sa.Column("description", sa.Text, nullable=True),
    sa.Column("nodes_json", sa.Text, nullable=False),  # store nodes as JSON string
    sa.Column("updated_at", sa.String(length=64), nullable=True),
)

# Optional sessions table for persistence (not required; session_store may use Redis)
sessions = sa.Table(
    "sessions",
    metadata,
    sa.Column("call_id", sa.String(length=128), primary_key=True),
    sa.Column("data_json", sa.Text, nullable=True),
    sa.Column("last_update", sa.String(length=64), nullable=True),
)
