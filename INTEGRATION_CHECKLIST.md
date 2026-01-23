# Integration Checkliste

Verwenden Sie diese Checkliste, um die Template-Funktionalität in Ihre Anwendung zu integrieren.

## ✅ Vor der Integration

- [ ] Python 3.11+ installiert
- [ ] FastAPI Projekt vorhanden
- [ ] SQLAlchemy Datenbank konfiguriert
- [ ] `fastapi_app_settings` Modul installiert

## 📦 Installation

```bash
# Option 1: Als editierbares Package
cd packages/fastapi_app_settings
pip install -e .

# Option 2: Normale Installation
pip install ./packages/fastapi_app_settings
```

- [ ] Modul installiert
- [ ] Dependencies aufgelöst (jinja2, fastapi, sqlalchemy, etc.)

## 🔧 Basis-Konfiguration

### 1. Router erstellen

```python
from fastapi_app_settings import create_settings_router

settings_router = create_settings_router(
    prefix="/api/settings",
    enable_templates=True,
)
```

- [ ] Router importiert
- [ ] `enable_templates=True` gesetzt
- [ ] Prefix angepasst (optional)

### 2. Router einbinden

```python
app.include_router(settings_router)
```

- [ ] Router zur App hinzugefügt
- [ ] App startet ohne Fehler

### 3. Testen

```bash
# Server starten
uvicorn main:app --reload

# Im Browser öffnen
# http://localhost:8000/api/settings/ui
```

- [ ] Server startet
- [ ] UI ist erreichbar
- [ ] Keine JavaScript-Fehler in der Browser-Konsole

## 🎨 Template-Anpassung (Optional)

### Option A: Eingebautes Template verwenden

```python
settings_router = create_settings_router(
    prefix="/api/settings",
    enable_templates=True,
    custom_template_name="settings_example.html"
)
```

- [ ] Template-Name gesetzt
- [ ] Template wird korrekt geladen

### Option B: Eigenes Template erstellen

1. Template-Verzeichnis erstellen:
```bash
mkdir -p templates/settings
```

2. Template erstellen (`templates/settings/my_settings.html`):
```html
{% extends "settings_base.html" %}

{% block content %}
<!-- Ihre Felder hier -->
{% endblock %}
```

3. Router konfigurieren:
```python
settings_router = create_settings_router(
    prefix="/api/settings",
    enable_templates=True,
    templates_directory="templates/settings",
    custom_template_name="my_settings.html"
)
```

- [ ] Template-Verzeichnis erstellt
- [ ] Template-Datei erstellt
- [ ] Router konfiguriert
- [ ] Template wird geladen

## ⚙️ Erweiterte Konfiguration

### Extra Settings definieren

1. Datei erstellen (`config/extra_settings.py`):
```python
ALLOWED_SETTINGS = [
    "project_name",
    "api_key",
    "max_upload_size",
]

PROTECTED_SETTINGS = [
    "api_key",
]

DEFAULT_SETTINGS_VALUES = {
    "project_name": "My Project",
    "max_upload_size": "10485760",
}
```

2. Router konfigurieren:
```python
settings_router = create_settings_router(
    prefix="/api/settings",
    app_root=".",
    extra_settings_file="config/extra_settings.py",
    enable_templates=True,
)
```

- [ ] Extra Settings Datei erstellt
- [ ] Router konfiguriert
- [ ] Settings werden erkannt

### Eigene Datenbank-Dependency

```python
from backend.database.base import get_db

settings_router = create_settings_router(
    prefix="/api/settings",
    get_db=get_db,
    enable_templates=True,
)
```

- [ ] `get_db` Funktion vorhanden
- [ ] Router verwendet eigene Dependency

## 🔒 Sicherheit

- [ ] Geschützte Einstellungen in `PROTECTED_SETTINGS` definiert
- [ ] Passwörter/API-Keys nicht in Templates angezeigt
- [ ] Authentifizierung eingerichtet (falls erforderlich)
- [ ] HTTPS in Produktion aktiviert

### Authentifizierung hinzufügen (Optional)

```python
from fastapi import Depends
from backend.auth import get_current_user

# In Ihrer App, nach Router-Erstellung
@settings_router.get("/ui", dependencies=[Depends(get_current_user)])
@settings_router.post("/ui/update", dependencies=[Depends(get_current_user)])
```

- [ ] Authentifizierung implementiert
- [ ] UI nur für autorisierte Benutzer zugänglich

## 🧪 Tests

### Manuelles Testen

1. **UI laden**
   - [ ] `/api/settings/ui` öffnet sich
   - [ ] Keine JavaScript-Fehler
   - [ ] Styling wird korrekt angezeigt

2. **Einstellung erstellen**
   - [ ] Neues Feld ausfüllen
   - [ ] Speichern klicken
   - [ ] Erfolgsmeldung erscheint

3. **Einstellung ändern**
   - [ ] Bestehenden Wert ändern
   - [ ] Speichern
   - [ ] Änderung wird übernommen

4. **Geschützte Einstellung**
   - [ ] Geschützte Einstellung wird nicht aktualisiert

### Automatisierte Tests

```bash
pytest tests/test_templates.py -v
```

- [ ] Alle Tests bestehen
- [ ] Keine Fehler oder Warnungen

## 📊 Monitoring

- [ ] Logs überprüfen (keine Fehler beim Template-Laden)
- [ ] Performance akzeptabel (< 200ms für UI-Laden)
- [ ] Keine Memory Leaks bei wiederholten Aufrufen

## 📝 Dokumentation

- [ ] Team über neue UI informiert
- [ ] Dokumentation für Endbenutzer erstellt
- [ ] README.md der App aktualisiert

## 🚀 Deployment

### Vor dem Deployment

- [ ] Templates im Build enthalten (MANIFEST.in vorhanden)
- [ ] Dependencies in requirements.txt/pyproject.toml
- [ ] Environment Variables korrekt gesetzt
- [ ] Datenbank-Migrationen durchgeführt

### Nach dem Deployment

- [ ] UI in Produktionsumgebung erreichbar
- [ ] Settings werden korrekt gespeichert
- [ ] Keine Fehler in Produktionslogs

## 🔄 Rollback-Plan

Falls Probleme auftreten:

```python
# Templates deaktivieren
settings_router = create_settings_router(
    prefix="/api/settings",
    enable_templates=False,  # ← Deaktivieren
)
```

- [ ] Rollback-Szenario getestet
- [ ] API-Endpunkte funktionieren weiterhin

## 📚 Nächste Schritte

Nach erfolgreicher Integration:

- [ ] Weitere Einstellungen hinzufügen
- [ ] Template nach Bedarf anpassen
- [ ] Validierung erweitern
- [ ] Benutzer-Feedback sammeln

## 🆘 Hilfe

Bei Problemen:

1. **Logs prüfen**: Server-Logs auf Fehler checken
2. **Dokumentation**: [TEMPLATE_USAGE.md](TEMPLATE_USAGE.md) lesen
3. **Demo testen**: `python demo.py` ausführen
4. **Tests laufen lassen**: `pytest tests/test_templates.py -v`

## ✨ Erfolg!

Wenn alle Punkte abgehakt sind, ist die Integration erfolgreich!

🎉 Die Settings-UI ist jetzt verfügbar unter:
```
http://your-domain.com/api/settings/ui
```
