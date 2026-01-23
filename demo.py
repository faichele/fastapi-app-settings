#!/usr/bin/env python3
"""
Minimales Demo-Script für die Template-Funktionalität.
Kann direkt ausgeführt werden ohne weitere Abhängigkeiten.
"""

import sys
from pathlib import Path

# Füge das Parent-Verzeichnis zum Python-Pfad hinzu
parent_path = Path(__file__).parent.parent
if str(parent_path) not in sys.path:
    sys.path.insert(0, str(parent_path))

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uvicorn

# Importiere das Modul
try:
    # Versuche als installiertes Package zu importieren
    from fastapi_app_settings import create_settings_router
    from fastapi_app_settings.models import Base
except ImportError:
    # Fallback für lokale Entwicklung
    from fastapi_app_settings.router import create_settings_router
    from fastapi_app_settings.models import Base

# In-Memory SQLite Datenbank für Demo
DATABASE_URL = "sqlite:///./demo_settings.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Erstelle Tabellen
Base.metadata.create_all(bind=engine)


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Erstelle FastAPI App
app = FastAPI(
    title="FastAPI App Settings - Demo",
    description="Demo der Template-Funktionalität",
    version="0.0.2"
)


# Erstelle Settings-Router mit Templates
settings_router = create_settings_router(
    prefix="/api/settings",
    get_db=get_db,
    enable_templates=True,
    custom_template_name="settings_example.html"
)

app.include_router(settings_router)


@app.get("/")
async def root():
    """Root endpoint mit Links."""
    return {
        "message": "FastAPI App Settings Demo",
        "links": {
            "settings_ui": "/api/settings/ui",
            "api_docs": "/docs",
            "settings_api": "/api/settings"
        }
    }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  FastAPI App Settings - Template Demo")
    print("="*70)
    print("\nServer startet...")
    print("\nVerfügbare URLs:")
    print("  • Settings UI:       http://localhost:8000/api/settings/ui")
    print("  • API Dokumentation: http://localhost:8000/docs")
    print("  • Root:              http://localhost:8000/")
    print("\nDrücken Sie CTRL+C zum Beenden\n")
    print("-"*70 + "\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
