"""Database integration boundary.

SQLite/SQLAlchemy session management, migrations, repositories, and later
vector-store metadata adapters will live here. It is intentionally not wired
into the in-memory meeting service until persistence is a product requirement.
"""
