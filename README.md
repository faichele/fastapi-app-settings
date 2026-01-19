# rideto-app-settings

Wiederverwendbares Modul für anwendungsweite Einstellungen mit FastAPI, SQLAlchemy und Pydantic.

Enthält:
- SettingsManager: Synchronisiert `.env`/ApplicationSettings und DB-Settings
- Router-Factory `create_settings_router`: bindet REST-Endpoints für Einstellungen ein
- SQLAlchemy/Pydantic-Modelle (`Setting`, `SettingBase`, `SettingCreate`, `SettingUpdate`, `SettingResponse`)
- Konstanten `ALLOWED_SETTINGS` und `PROTECTED_SETTINGS`

## Installation

Aus dem Unterverzeichnis installieren (PEP 621, setuptools):

```bash
# Aus dem Repo-Root
pip install ./backend/fastapi_app_settings
# oder als Editable
pip install -e ./backend/fastapi_app_settings
```

Alternativ via pyproject Abhängigkeit (PEP 508 direct reference):

```toml
# pyproject.toml eines Consumer-Projekts
[project]
dependencies = [
  "rideto-app-settings @ file:///${PROJECT_ROOT}/backend/app_settings",
]
```

## Nutzung

### 1) Router einbinden

```python
from app_settings import create_settings_router

app.include_router(create_settings_router(prefix="/api/settings"))
```

### 2) SettingsManager initialisieren (typisch beim Startup)

```python
from app_settings import settings_manager
from my_db import get_db

# innerhalb eines Startup-Hooks
db = next(get_db())
settings_manager.initialize(db)
```

### 3) Zugriff auf Settings

```python
from app_settings import settings_manager

value = settings_manager.get_setting("thumbnail_directory")
settings_manager.set_setting("thumbnail_directory", "static/thumb")
```

## Import-Pfade

- Als installiertes Modul: `from app_settings import ...`
- Innerhalb des bestehenden Projekts können weiterhin die bisherigen Pfade genutzt werden:
  - `from backend.app_settings import ...`

## Entwickeln

Lokale Tests/Typprüfung (optional):

```bash
pip install -e ./backend/fastapi_app_settings[dev]
pytest -q
ruff check .
mypy .
```

## Hinweise

- Das Modul erwartet, dass die SQLAlchemy `Base` und die DB-Session (`get_db`) in der konsumierenden App bereitstehen. Die Models registrieren sich über `Base`.
- Timezone-aware Timestamps (UTC) werden für `created_date`/`updated_date` verwendet.
- Einige Einstellungen sind bewusst geschützt (`PROTECTED_SETTINGS`) und werden nicht über den REST-Router exponiert.

