"""FastAPI launcher."""

from __future__ import annotations

import os

import uvicorn


def main():
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "5000"))
    print(f"Starting FastAPI + Socket.IO app on http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False, log_level="info")


if __name__ == "__main__":
    main()
