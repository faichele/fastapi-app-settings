# Template-Funktionalität - Übersicht

## 🎉 Neue Features

Das `fastapi_app_settings` Modul unterstützt jetzt Jinja2-Templates für eine Web-basierte Einstellungs-UI!

## 📁 Neue Dateien

### Templates
- `templates/settings_base.html` - Basis-Template (Rahmen für eigene Formulare)
- `templates/settings_example.html` - Vollständiges Beispiel-Template

### Dokumentation
- `TEMPLATE_USAGE.md` - Detaillierte Dokumentation zur Template-Nutzung
- `QUICKSTART.md` - Schnellstart-Anleitung
- `README.md` - Wurde aktualisiert mit Template-Informationen

### Beispiele & Tests
- `example_template_usage.py` - Verschiedene Nutzungsbeispiele
- `demo.py` - Minimales Demo-Script (sofort ausführbar)
- `tests/test_templates.py` - Tests für Template-Funktionalität

### Konfiguration
- `MANIFEST.in` - Für die korrekte Paketierung der Templates
- `pyproject.toml` - Aktualisiert mit jinja2-Abhängigkeit

## 🚀 Schnellstart

```bash
# 1. Ins Modul-Verzeichnis wechseln
cd packages/fastapi_app_settings

# 2. Demo starten
python demo.py

# 3. Im Browser öffnen
# http://localhost:8000/api/settings/ui
```

## 💡 Verwendung

### Basis-Verwendung

```python
from fastapi_app_settings.router import create_settings_router

settings_router = create_settings_router(
    prefix="/api/settings",
    enable_templates=True,  # ← Templates aktivieren
)

app.include_router(settings_router)
```

### Mit eigenem Template

```python
settings_router = create_settings_router(
    prefix="/api/settings",
    enable_templates=True,
    templates_directory="my_templates",
    custom_template_name="my_settings.html"
)
```

## 📋 Basis-Template Blöcke

Das `settings_base.html` Template bietet folgende überschreibbare Blöcke:

### Inhalt
- `title` - Browser-Tab Titel
- `page_title` - Hauptüberschrift
- `page_description` - Beschreibung
- `content` - Hauptinhalt (Formularfelder)

### Styling
- `extra_head` - Zusätzliche Head-Inhalte
- `extra_styles` - Eigene CSS-Styles

### Formular
- `form_action` - Submit-URL
- `form_buttons` - Buttons (Speichern, Zurücksetzen)
- `messages` - Erfolgs-/Fehlermeldungen

### JavaScript
- `extra_scripts` - Eigene Scripts
- `form_submit_handler` - Submit-Handler
- `extra_js_init` - Initialisierung

## 🎨 Beispiel: Eigenes Template

```html
{% extends "settings_base.html" %}

{% block title %}Projekt-Einstellungen{% endblock %}

{% block content %}
<div class="settings-section">
    <h3>Allgemeine Einstellungen</h3>
    
    <div class="form-group">
        <label for="project_name" class="form-label">Projektname</label>
        <input type="text" class="form-control" 
               name="project_name" 
               value="{{ settings.project_name | default('') }}">
    </div>
</div>
{% endblock %}
```

## 🔒 Sicherheit

- **Geschützte Einstellungen**: Einstellungen in `PROTECTED_SETTINGS` werden automatisch nicht über UI aktualisiert
- **Validierung**: Nur Einstellungen in `ALLOWED_SETTINGS` können geändert werden
- **CSRF**: Kann durch eigene Middleware ergänzt werden

## 🔧 API-Endpunkte

### Neue Template-Endpunkte

| Methode | Endpunkt | Beschreibung |
|---------|----------|--------------|
| GET | `/api/settings/ui` | Zeigt Settings-Formular |
| POST | `/api/settings/ui/update` | Verarbeitet Formular-Submission |

### Bestehende API-Endpunkte (bleiben unverändert)

| Methode | Endpunkt | Beschreibung |
|---------|----------|--------------|
| GET | `/api/settings` | Alle Einstellungen |
| POST | `/api/settings` | Neue Einstellung erstellen |
| GET | `/api/settings/{name}` | Einstellung abrufen |
| PUT | `/api/settings/{name}` | Einstellung aktualisieren |
| DELETE | `/api/settings/{name}` | Einstellung löschen |

## 📦 Abhängigkeiten

Neu hinzugefügt:
- `jinja2>=3.1` - Template-Engine

Bestehend:
- `fastapi>=0.110`
- `sqlalchemy>=2.0`
- `pydantic>=2.6`
- `pillow>=10.0`

## 🧪 Tests

```bash
# Alle Tests ausführen
pytest tests/

# Nur Template-Tests
pytest tests/test_templates.py -v
```

## 📚 Weitere Dokumentation

- **Detaillierte Anleitung**: [TEMPLATE_USAGE.md](TEMPLATE_USAGE.md)
- **Schnellstart**: [QUICKSTART.md](QUICKSTART.md)
- **Hauptdokumentation**: [README.md](README.md)
- **Beispiele**: [example_template_usage.py](example_template_usage.py)

## 🔄 Migration bestehender Anwendungen

Bestehende Anwendungen funktionieren weiterhin ohne Änderungen. Die Template-Funktionalität ist **optional** und muss explizit aktiviert werden:

```python
# Alt (funktioniert weiterhin)
router = create_settings_router(prefix="/api/settings")

# Neu (mit Templates)
router = create_settings_router(
    prefix="/api/settings",
    enable_templates=True
)
```

## 🎯 Anwendungsfälle

### 1. Einfache Konfiguration
- Nutzen Sie `settings_example.html` als Ausgangspunkt
- Keine eigenen Templates nötig

### 2. Angepasstes Design
- Erstellen Sie eigene Templates basierend auf `settings_base.html`
- Verwenden Sie Bootstrap oder eigene CSS-Frameworks

### 3. Komplexe Formulare
- Mehrere Sektionen
- Validierung
- Dynamische Felder mit JavaScript

### 4. Admin-Interface
- Integration in bestehende Admin-Panels
- Authentifizierung/Autorisierung über FastAPI Dependencies

## 🐛 Troubleshooting

### Template nicht gefunden
```
Problem: TemplateNotFound: 'my_settings.html'
Lösung: Überprüfen Sie templates_directory und custom_template_name
```

### Settings werden nicht gespeichert
```
Problem: Änderungen werden nicht übernommen
Lösung: Prüfen Sie ALLOWED_SETTINGS und PROTECTED_SETTINGS
```

### UI zeigt keine Daten
```
Problem: Formular ist leer
Lösung: Stellen Sie sicher, dass Settings in der DB existieren
```

## 🤝 Beitragen

Das Modul ist erweiterbar. Neue Features können hinzugefügt werden:
- Zusätzliche Template-Blöcke
- Weitere UI-Komponenten
- Erweiterte Validierung
- AJAX-Support

## 📝 Lizenz

MIT License - Siehe [LICENSE](LICENSE)

## ✨ Zusammenfassung

**Das Modul bietet jetzt:**
✅ Basis-Template für Einstellungs-Formulare
✅ Beispiel-Template mit allen Features
✅ Vollständige Dokumentation
✅ Funktionierende Beispiele
✅ Tests für Template-Funktionalität
✅ Bootstrap 5 für responsives Design
✅ Einfache Integration in bestehende Apps
✅ Rückwärtskompatibilität
