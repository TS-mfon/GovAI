"""Vercel Python serverless entrypoint for the GovAI backend (FastAPI).

Exports the FastAPI `app` for Vercel's ASGI Python runtime.
All requests are routed here by `../vercel.json`.

Local dev still uses `uvicorn main:app` from the `backend/` directory.
"""
from main import app  # noqa: F401  (Vercel Python runtime auto-detects the ASGI `app`)