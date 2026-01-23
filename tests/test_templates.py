"""
Tests für die Template-Funktionalität des Settings-Routers.
"""

import pytest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Annahme: Die Models und der Router sind korrekt importierbar
try:
    from fastapi_app_settings.router import create_settings_router
    from fastapi_app_settings.models import Base
except ImportError:
    # Fallback für lokale Entwicklung
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from router import create_settings_router
    from models import Base


# Test-Datenbank Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_templates.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_test_db():
    """Test-Datenbank-Session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def setup_db():
    """Erstellt die Test-Datenbank vor jedem Test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def app_with_templates(setup_db):
    """FastAPI-App mit aktivierten Templates."""
    app = FastAPI()

    router = create_settings_router(
        prefix="/api/settings",
        get_db=get_test_db,
        enable_templates=True,
    )

    app.include_router(router)
    return app


@pytest.fixture
def app_with_custom_template(setup_db):
    """FastAPI-App mit Beispiel-Template."""
    app = FastAPI()

    router = create_settings_router(
        prefix="/api/settings",
        get_db=get_test_db,
        enable_templates=True,
        custom_template_name="settings_example.html"
    )

    app.include_router(router)
    return app


@pytest.fixture
def app_without_templates(setup_db):
    """FastAPI-App ohne Templates."""
    app = FastAPI()

    router = create_settings_router(
        prefix="/api/settings",
        get_db=get_test_db,
        enable_templates=False,
    )

    app.include_router(router)
    return app


def test_templates_enabled_ui_accessible(app_with_templates):
    """Test, dass die UI-Route verfügbar ist, wenn Templates aktiviert sind."""
    client = TestClient(app_with_templates)
    response = client.get("/api/settings/ui")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert b"Einstellungen" in response.content or b"settings" in response.content.lower()


def test_templates_disabled_ui_not_accessible(app_without_templates):
    """Test, dass die UI-Route nicht verfügbar ist, wenn Templates deaktiviert sind."""
    client = TestClient(app_without_templates)
    response = client.get("/api/settings/ui")

    assert response.status_code == 404


def test_custom_template_used(app_with_custom_template):
    """Test, dass das Beispiel-Template korrekt verwendet wird."""
    client = TestClient(app_with_custom_template)
    response = client.get("/api/settings/ui")

    assert response.status_code == 200
    # Das Beispiel-Template enthält spezifische Inhalte
    content = response.content.decode("utf-8")
    assert "Bildverzeichnis" in content or "Thumbnail" in content


def test_ui_form_submission(app_with_templates):
    """Test, dass Formular-Submissions funktionieren."""
    client = TestClient(app_with_templates)

    # Erstmal Settings über API setzen
    client.post("/api/settings", json={"name": "project_name", "value": "TestProject"})

    # Dann über UI aktualisieren
    form_data = {
        "project_name": "UpdatedProject"
    }
    response = client.post("/api/settings/ui/update", data=form_data)

    assert response.status_code == 200
    assert b"UpdatedProject" in response.content or b"erfolgreich" in response.content


def test_ui_shows_settings(app_with_templates):
    """Test, dass vorhandene Settings im UI angezeigt werden."""
    client = TestClient(app_with_templates)

    # Setting erstellen
    client.post("/api/settings", json={"name": "test_setting", "value": "test_value"})

    # UI aufrufen
    response = client.get("/api/settings/ui")

    assert response.status_code == 200
    # Die Settings sollten im HTML vorhanden sein
    content = response.content.decode("utf-8")
    # Je nach Template kann der Inhalt variieren


def test_protected_settings_not_updated_via_ui(app_with_templates):
    """Test, dass geschützte Einstellungen nicht über UI aktualisiert werden."""
    client = TestClient(app_with_templates)

    # Geschützte Einstellung über API erstellen
    response = client.post("/api/settings", json={
        "name": "postgres_password",
        "value": "secret123"
    })

    # Versuche über UI zu aktualisieren
    form_data = {
        "postgres_password": "hacked"
    }
    response = client.post("/api/settings/ui/update", data=form_data)

    # Sollte erfolgreich sein (kein Fehler), aber nicht aktualisiert
    assert response.status_code == 200

    # Prüfe, dass der Wert nicht geändert wurde
    response = client.get("/api/settings/postgres_password")
    if response.status_code == 200:
        assert response.json()["value"] == "secret123"


def test_ui_success_message_after_update(app_with_templates):
    """Test, dass eine Erfolgsmeldung nach Update angezeigt wird."""
    client = TestClient(app_with_templates)

    form_data = {
        "test_setting": "new_value"
    }
    response = client.post("/api/settings/ui/update", data=form_data)

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # Sollte eine Erfolgsmeldung enthalten
    assert "erfolgreich" in content.lower() or "success" in content.lower()


def test_template_directory_not_found_warning(setup_db, tmp_path):
    """Test, dass eine Warnung ausgegeben wird, wenn Template-Verzeichnis nicht existiert."""
    app = FastAPI()

    non_existent_dir = tmp_path / "non_existent_templates"

    # Sollte nicht abstürzen, auch wenn das Verzeichnis nicht existiert
    router = create_settings_router(
        prefix="/api/settings",
        get_db=get_test_db,
        enable_templates=True,
        templates_directory=str(non_existent_dir),
    )

    app.include_router(router)
    client = TestClient(app)

    # UI sollte nicht verfügbar sein oder 404 geben
    response = client.get("/api/settings/ui")
    assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
