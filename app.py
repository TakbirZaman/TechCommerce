"""Vercel FastAPI entrypoint; the shared application remains in main.py."""
from main import app

__all__ = ["app"]
