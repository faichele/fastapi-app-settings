# AGENTS.md — fastapi-app-settings

## Zweck

Dieses Paket verwaltet anwendungsweite Einstellungen über eine Kombination aus Pydantic-
Settings, SQLAlchemy und FastAPI. Es stellt `SettingsManager`, Pydantic-Schemas, dynamisch
erzeugte ORM-Modelle und `create_settings_router()` bereit.

## Wichtige Regeln

- Oeffentliche Symbole ueber `fastapi_app_settings.__init__` exportieren.
- ORM-Modelle nicht statisch mit einer fremden Base definieren. `create_setting_models()` bzw.
  `configure_setting_models()` mit der Base der konsumierenden Anwendung verwenden.
- Das Modell-Caching pro Base und Tabellenpräfix in `model_factory.py` erhalten.
- Das Tabellenpräfix bewusst setzen und bei Änderungen Migrationen der konsumierenden Anwendung
  berücksichtigen.
- Geschützte Einstellungen (`PROTECTED_SETTINGS`) dürfen nicht über den REST-Router gelesen oder
  geändert werden; schreibgeschützte Einstellungen (`READONLY_SETTINGS`) ebenfalls respektieren.
- `fastapi_shared_orm` liefert die gemeinsame SQLAlchemy-Base; Engine und Session gehören in die
  Anwendung oder werden beim standalone Betrieb über `database_url`/`session_factory` injiziert.

## Projektstruktur

- `settings_manager.py`: Synchronisierung von App-Settings, Datenbank, `.env` und dynamischen
  Zusatzsettings
- `model_factory.py`: Erzeugung und Konfiguration der `Setting`-ORM-Modelle
- `models.py`: Pydantic-Schemas sowie erlaubte, geschützte und schreibgeschützte Settings
- `router.py`: FastAPI-Router, REST-Endpunkte, optionale Zusatzrouter und Template-UI
- `templates/`: mitgelieferte Jinja2-Templates
- `tests/`: Router-, Model-Factory-, Zusatzsettings- und Packaging-Tests

## Integrationsregeln

- `create_settings_router()` benötigt `get_db`, `session_factory`, `database_url` oder eine
  verfügbare `backend.database.base.get_db`-Dependency.
- Anwendungsspezifische Settings-Dateien werden über `app_root` und
  `extra_settings_file` geladen; Namen der Variablen (`ALLOWED_SETTINGS`,
  `PROTECTED_SETTINGS`, `DEFAULT_SETTINGS_VALUES`, `EXTRA_SETTINGS_MAP`) bei Erweiterungen
  dokumentieren und nicht stillschweigend ändern.
- Dynamische Resolver erhalten einen `SettingsManagerContext`; sie sollen keine globalen
  Seiteneffekte erzeugen.
- Templates nur über die vorhandene `enable_templates`-Option und den vorgesehenen
  Template-Pfad einbinden. Neue Templates in `pyproject.toml` als Package-Daten berücksichtigen.
- Bei dynamischen Zusatzroutern und Modulen Fehler sichtbar loggen; keine stillen Erfolgswerte
  zurückgeben.

## Vorgehen bei Änderungen

1. Zuerst prüfen, ob die Änderung `models.py`, `model_factory.py`, `settings_manager.py` und
   `router.py` gemeinsam betrifft.
2. Bei Änderungen an API-Verhalten passende Tests in `tests/` ergänzen oder anpassen.
3. Bei Änderungen an Tabellenname, Base-Bindung oder Präfix eine Migration im Consumer-Projekt
   einplanen.
4. Dokumentation und Beispiele aktualisieren, wenn neue Router-Optionen oder Konfigurationsvariablen
   hinzukommen.

## Qualitaetssicherung

Aus dem Paketverzeichnis:

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
mypy .
```

Besonders prüfen: Modellregistrierung auf einer injizierten Base, Defaults aus Zusatzsettings,
Schutz-/Readonly-Regeln, standalone `database_url` und die ausgelieferten Templates.

## Nicht tun

- Keine Datenbank-Engine oder globale Session als versteckten Paketzustand einführen.
- Keine Secrets aus geschützten Settings in API-Antworten, Defaults oder Logs aufnehmen.
- Keine manuellen Änderungen an `.idea`- oder Cache-Dateien.
- Keine globale Alias-Konfiguration der ORM-Modelle ändern, ohne die Auswirkungen auf bereits
  importierte Module und Consumer-Anwendungen zu testen.
