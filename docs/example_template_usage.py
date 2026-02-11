#!/usr/bin/env python3
"""
Beispiel zur Verwendung der Template-Funktionalität des fastapi_app_settings Moduls.

Dieses Script zeigt verschiedene Konfigurationsmöglichkeiten für die Template-Integration.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

# Beispiel 1: Minimale Konfiguration mit eingebauten Templates
def create_app_with_builtin_templates():
    """Verwendet die eingebauten Templates des Moduls."""
    app = FastAPI(title="Settings UI - Eingebaute Templates")

    from fastapi_app_settings.router import create_settings_router

    settings_router = create_settings_router(
        prefix="/api/settings",
        enable_templates=True,  # Templates aktivieren
        # Keine weitere Konfiguration nötig - nutzt eingebaute Templates
    )

    app.include_router(settings_router)

    print("✓ App mit eingebauten Templates erstellt")
    print("  Zugriff auf UI: http://localhost:8000/api/settings/ui")

    return app


# Beispiel 2: Eigenes Template verwenden
def create_app_with_custom_template():
    """Verwendet ein eigenes Template."""
    from pathlib import Path
    app = FastAPI(title="Settings UI - Eigenes Template")

    from fastapi_app_settings.router import create_settings_router

    # Annahme: Eigene Templates liegen in ./my_templates/
    templates_dir = Path(__file__).parent / "my_templates"

    settings_router = create_settings_router(
        prefix="/api/settings",
        enable_templates=True,
        templates_directory=str(templates_dir),
        custom_template_name="my_settings.html"
    )

    app.include_router(settings_router)

    print("✓ App mit eigenem Template erstellt")
    print(f"  Template-Verzeichnis: {templates_dir}")
    print("  Zugriff auf UI: http://localhost:8000/api/settings/ui")

    return app


# Beispiel 3: Mit Beispiel-Template
def create_app_with_example_template():
    """Verwendet das mitgelieferte Beispiel-Template."""
    app = FastAPI(title="Settings UI - Beispiel Template")

    from fastapi_app_settings.router import create_settings_router

    settings_router = create_settings_router(
        prefix="/api/settings",
        enable_templates=True,
        custom_template_name="settings_example.html"  # Nutzt das Beispiel-Template
    )

    app.include_router(settings_router)

    print("✓ App mit Beispiel-Template erstellt")
    print("  Zugriff auf UI: http://localhost:8000/api/settings/ui")

    return app


# Beispiel 4: Vollständige Konfiguration mit allen Optionen
def create_app_full_config():
    """Zeigt alle verfügbaren Konfigurationsoptionen."""
    from pathlib import Path
    app = FastAPI(
        title="Settings UI - Vollständig konfiguriert",
        description="Beispiel mit allen Template-Optionen"
    )

    from fastapi_app_settings.router import create_settings_router

    app_root = Path(__file__).parent

    settings_router = create_settings_router(
        prefix="/api/settings",
        # get_db=my_custom_get_db,  # Optional: eigene DB-Dependency
        app_root=str(app_root),
        extra_settings_file="config/extra_settings.py",  # Optional
        enable_templates=True,
        templates_directory="templates/settings",  # Relativ zu app_root
        custom_template_name="custom_settings.html"
    )

    app.include_router(settings_router)

    # Optional: Statische Dateien für eigene CSS/JS
    # app.mount("/static", StaticFiles(directory="static"), name="static")

    print("✓ App mit vollständiger Konfiguration erstellt")
    print(f"  App-Root: {app_root}")
    print("  Zugriff auf UI: http://localhost:8000/api/settings/ui")
    print("  API-Dokumentation: http://localhost:8000/docs")

    return app


# Beispiel 5: Mehrere Settings-Router (z.B. für unterschiedliche Bereiche)
def create_app_multiple_routers():
    """Zeigt, wie man mehrere Settings-Router für verschiedene Bereiche nutzt."""
    app = FastAPI(title="Settings UI - Multiple Router")

    from fastapi_app_settings.router import create_settings_router

    # Router für allgemeine Einstellungen
    general_router = create_settings_router(
        prefix="/api/settings/general",
        enable_templates=True,
        custom_template_name="settings_base.html"
    )

    # Router für Admin-Einstellungen (könnte andere ALLOWED_SETTINGS haben)
    # admin_router = create_settings_router(
    #     prefix="/api/settings/admin",
    #     extra_settings_file="config/admin_settings.py",
    #     enable_templates=True,
    #     custom_template_name="settings_admin.html"
    # )

    app.include_router(general_router)
    # app.include_router(admin_router)

    print("✓ App mit mehreren Settings-Routern erstellt")
    print("  Allgemeine Einstellungen: http://localhost:8000/api/settings/general/ui")
    # print("  Admin Einstellungen: http://localhost:8000/api/settings/admin/ui")

    return app


def main():
    """Hauptfunktion zum Starten der Beispiel-Anwendung."""
    print("\n" + "="*60)
    print("FastAPI App Settings - Template-Beispiele")
    print("="*60 + "\n")

    print("Wählen Sie ein Beispiel:")
    print("1. Eingebaute Templates (Standard)")
    print("2. Eigenes Template")
    print("3. Beispiel-Template")
    print("4. Vollständige Konfiguration")
    print("5. Multiple Router")
    print()

    choice = input("Ihre Wahl (1-5) [1]: ").strip() or "1"

    app_creators = {
        "1": create_app_with_builtin_templates,
        "2": create_app_with_custom_template,
        "3": create_app_with_example_template,
        "4": create_app_full_config,
        "5": create_app_multiple_routers,
    }

    if choice not in app_creators:
        print(f"Ungültige Wahl: {choice}. Verwende Standard (1).")
        choice = "1"

    print(f"\nStarte Beispiel {choice}...\n")
    app = app_creators[choice]()

    print("\n" + "-"*60)
    print("Server wird gestartet...")
    print("-"*60 + "\n")

    # Server starten
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    # Für schnelles Testen: Nutze Beispiel 3 (mit Beispiel-Template)
    # Um interaktiv zu wählen, rufe main() auf

    # Schnellstart mit Beispiel-Template:
    app = create_app_with_example_template()

    print("\n" + "-"*60)
    print("Server wird gestartet...")
    print("Drücken Sie CTRL+C zum Beenden")
    print("-"*60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

    # Für interaktive Auswahl, kommentieren Sie die obigen Zeilen aus
    # und verwenden Sie stattdessen:
    # main()
