# Schnellstart: Template-Funktionalität

## In 5 Minuten zur funktionierenden Settings-UI

### 1. Installation

```bash
cd packages/fastapi_app_settings
pip install -e .
```

### 2. Minimales Beispiel

Erstellen Sie eine Datei `quickstart.py`:

```python
from fastapi import FastAPI
from fastapi_app_settings.router import create_settings_router
import uvicorn

app = FastAPI(title="Settings UI Quickstart")

# Router mit Templates erstellen
settings_router = create_settings_router(
    prefix="/api/settings",
    enable_templates=True,
    custom_template_name="settings_example.html"
)

app.include_router(settings_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3. Starten

```bash
python quickstart.py
```

### 4. Öffnen Sie im Browser

```
http://localhost:8000/api/settings/ui
```

## Eigenes Template in 3 Schritten

### 1. Template erstellen

Erstellen Sie `templates/my_settings.html`:

```html
{% extends "settings_base.html" %}

{% block title %}Meine Einstellungen{% endblock %}

{% block content %}
<div class="settings-section">
    <h3>Projekt-Konfiguration</h3>
    
    <div class="form-group">
        <label for="project_name" class="form-label">Projektname</label>
        <input type="text" class="form-control" 
               name="project_name" 
               value="{{ settings.project_name | default('') }}">
    </div>
</div>
{% endblock %}
```

### 2. Router konfigurieren

```python
settings_router = create_settings_router(
    prefix="/api/settings",
    enable_templates=True,
    templates_directory="templates",
    custom_template_name="my_settings.html"
)
```

### 3. Fertig!

Ihre eigene Settings-UI ist einsatzbereit.

## Nächste Schritte

- Lesen Sie [TEMPLATE_USAGE.md](TEMPLATE_USAGE.md) für detaillierte Dokumentation
- Schauen Sie sich [example_template_usage.py](example_template_usage.py) für weitere Beispiele an
- Passen Sie das Template nach Ihren Bedürfnissen an

## Häufige Anwendungsfälle

### Mit bestehender Datenbank

```python
from backend.database.base import get_db

settings_router = create_settings_router(
    prefix="/api/settings",
    get_db=get_db,
    enable_templates=True
)
```

### Mit eigenen ALLOWED_SETTINGS

Erstellen Sie `config/my_settings.py`:

```python
ALLOWED_SETTINGS = [
    "project_name",
    "api_key",
    "max_upload_size",
]

PROTECTED_SETTINGS = [
    "api_key",  # Nicht über UI änderbar
]

DEFAULT_SETTINGS_VALUES = {
    "project_name": "My Project",
    "max_upload_size": "10485760",
}
```

Router konfigurieren:

```python
settings_router = create_settings_router(
    prefix="/api/settings",
    app_root=".",
    extra_settings_file="config/my_settings.py",
    enable_templates=True
)
```

## Hilfe

Bei Problemen:
1. Prüfen Sie die Server-Logs
2. Öffnen Sie `/docs` für die API-Dokumentation
3. Lesen Sie die vollständige Dokumentation in [TEMPLATE_USAGE.md](TEMPLATE_USAGE.md)
