"""
Configuration for Pacific Crest Estates API.

Render.com deployment notes:
- Render automatically injects environment variables you set in the dashboard.
- If you create a Render PostgreSQL instance and link it to this service,
  Render sets DATABASE_URL for you (starts with postgres://). We rewrite the
  scheme to postgresql:// so SQLAlchemy accepts it.
- If no DATABASE_URL is set, we fall back to a local SQLite file (great for
  development and for Render with an attached persistent Disk).
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def get_database_uri():
    uri = os.environ.get("DATABASE_URL")
    if uri:
        # Render's Postgres URL uses the old 'postgres://' scheme.
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri
    # SQLite fallback. If a Render persistent Disk is mounted at /var/data
    # (see render.yaml), keep the database there so it survives deploys.
    # Otherwise use a file next to app.py (local dev / ephemeral filesystem).
    if os.path.isdir("/var/data") and os.access("/var/data", os.W_OK):
        return "sqlite:////var/data/estate.db"
    return "sqlite:///" + os.path.join(BASE_DIR, "estate.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False

    # Your deployed FRONTEND URL — the backend reads/uses this value and
    # automatically allows it for CORS. Replace the placeholder with your real
    # frontend domain (e.g. https://pacific-crest-estates.netlify.app), or set
    # the FRONTEND_URL environment variable on Render.
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://jolly-beijinho-1f918a.netlify.app").rstrip("/")

    # Comma-separated list of origins allowed to call the API (CORS).
    # Use "*" during development; set your frontend domain in production.
    # FRONTEND_URL (above) is always added to the allowed origins automatically.
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # Simple shared secret to protect the admin submissions endpoint.
    ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "change-me-admin-secret")

    # Fixed refundable holding deposit (USD) simulated via PayPal mock.
    HOLDING_DEPOSIT_USD = float(os.environ.get("HOLDING_DEPOSIT_USD", "1000.00"))
