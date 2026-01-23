# Template-Nutzung für fastapi_app_settings

## Übersicht

Das `fastapi_app_settings` Modul bietet jetzt Jinja2-Template-Unterstützung für die Darstellung von Einstellungs-Formularen. Das Basis-Template `settings_base.html` dient als Rahmen für anwendungsspezifische Formulare.

## Aktivierung der Template-Funktionalität

```python
from fastapi import FastAPI
from fastapi_app_settings.router import create_settings_router
from backend.database.base import get_db

app = FastAPI()

# Template-Funktionalität aktivieren
settings_router = create_settings_router(
    prefix="/api/settings",
    get_db=get_db,
    enable_templates=True,  # Templates aktivieren
    templates_directory=None,  # None = nutze eingebaute Templates
    custom_template_name="settings_example.html"  # Optional: eigenes Template
)

app.include_router(settings_router)
```

## Verwendung des Basis-Templates

Das Basis-Template (`settings_base.html`) bietet folgende Blöcke zur Überschreibung:

### Haupt-Blöcke

- `title`: Seitentitel im Browser-Tab
- `page_title`: Hauptüberschrift auf der Seite
- `page_description`: Beschreibungstext unter der Überschrift
- `content`: Hauptinhalt des Formulars (hier kommen Ihre Formularfelder)
- `form_action`: URL für das Formular-Submit (Standard: `/api/settings/update`)

### Style-Blöcke

- `extra_head`: Zusätzliche `<head>`-Inhalte
- `extra_styles`: Zusätzliche CSS-Styles

### Formular-Blöcke

- `form_buttons`: Submit-, Reset- und weitere Buttons
- `submit_button_text`: Text des Speichern-Buttons
- `reset_button_text`: Text des Zurücksetzen-Buttons
- `extra_buttons`: Zusätzliche Buttons

### Nachrichten-Block

- `messages`: Bereich für Erfolgs-, Fehler- und Warnmeldungen

### JavaScript-Blöcke

- `extra_scripts`: Zusätzliche Script-Tags
- `form_submit_handler`: JavaScript für Submit-Handling
- `extra_js_init`: JavaScript-Initialisierung

## Beispiel: Eigenes Template erstellen

Erstellen Sie eine Datei `my_settings.html`:

```html
{% extends "settings_base.html" %}

{% block title %}Meine Einstellungen{% endblock %}

{% block page_title %}Anwendungs-Konfiguration{% endblock %}

{% block page_description %}
    Konfigurieren Sie hier die Einstellungen Ihrer Anwendung.
{% endblock %}

{% block content %}
<div class="settings-section">
    <h3>Allgemeine Einstellungen</h3>
    
    <div class="form-group">
        <label for="project_name" class="form-label">Projektname</label>
        <input type="text" class="form-control" id="project_name" 
               name="project_name" 
               value="{{ settings.project_name | default('') }}" 
               required>
        <small class="form-text text-muted">
            Der Name Ihres Projekts.
        </small>
    </div>

    <div class="form-group">
        <label for="environment" class="form-label">Umgebung</label>
        <select class="form-select" id="environment" name="environment">
            <option value="development" 
                    {% if settings.environment == 'development' %}selected{% endif %}>
                Development
            </option>
            <option value="production" 
                    {% if settings.environment == 'production' %}selected{% endif %}>
                Production
            </option>
        </select>
    </div>
</div>

<div class="settings-section">
    <h3>Verzeichnisse</h3>
    
    <div class="form-group">
        <label for="image_directory" class="form-label">Bildverzeichnis</label>
        <input type="text" class="form-control" id="image_directory" 
               name="image_directory" 
               value="{{ settings.image_directory | default('static/images') }}">
    </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script>
    // Eigene Validierung
    document.getElementById('settingsForm').addEventListener('submit', function(e) {
        const projectName = document.getElementById('project_name').value.trim();
        if (projectName.length < 3) {
            e.preventDefault();
            alert('Der Projektname muss mindestens 3 Zeichen lang sein.');
            return false;
        }
    });
</script>
{% endblock %}
```

## Template-Konfigurationsoptionen

### Option 1: Eingebaute Templates verwenden

```python
settings_router = create_settings_router(
    enable_templates=True,
    # templates_directory wird nicht angegeben
    custom_template_name="settings_base.html"  # oder "settings_example.html"
)
```

### Option 2: Eigenes Template-Verzeichnis

```python
settings_router = create_settings_router(
    enable_templates=True,
    app_root="/path/to/your/app",
    templates_directory="my_templates",  # relativ zu app_root
    custom_template_name="my_settings.html"
)
```

### Option 3: Absoluter Pfad zum Template-Verzeichnis

```python
from pathlib import Path

settings_router = create_settings_router(
    enable_templates=True,
    templates_directory=Path("/absolute/path/to/templates"),
    custom_template_name="my_settings.html"
)
```

## Verfügbare Template-Variablen

Im Template stehen folgende Variablen zur Verfügung:

- `request`: FastAPI Request-Objekt
- `settings`: Dictionary mit allen Einstellungen
- `form_action`: URL für das Formular-Submit
- `success_message`: Erfolgsmeldung (nach erfolgreichem Update)
- `error_message`: Fehlermeldung (bei Fehler)
- `warning_message`: Warnmeldung

## Zugriff auf die UI

Nach der Konfiguration ist die Einstellungs-UI unter folgenden URLs verfügbar:

- **GET** `/api/settings/ui` - Zeigt das Einstellungsformular an
- **POST** `/api/settings/ui/update` - Verarbeitet Formular-Submissions

## Geschützte Einstellungen

Geschützte Einstellungen (z.B. Passwörter, API-Keys) werden automatisch:
- Nicht im Formular angezeigt (außer Sie fügen sie manuell hinzu)
- Nicht über das Formular aktualisiert

Um geschützte Einstellungen anzuzeigen (aber nicht editierbar):

```html
<div class="settings-section protected-setting">
    <h3>Geschützte Einstellungen (nur lesbar)</h3>
    
    <div class="form-group">
        <label class="form-label">Datenbank-Server</label>
        <input type="text" class="form-control" 
               value="{{ settings.postgres_server | default('localhost') }}" 
               disabled readonly>
    </div>
</div>
```

## Styling

Das Basis-Template nutzt Bootstrap 5 für grundlegendes Styling. Sie können:

1. **Bootstrap überschreiben**: Eigene CSS-Klassen im `extra_styles`-Block definieren
2. **Anderes Framework nutzen**: Eigenes Template erstellen ohne Bootstrap
3. **Inline-Styles**: Direkt in Ihren HTML-Elementen

## Best Practices

1. **Validierung**: Nutzen Sie den `form_submit_handler`-Block für clientseitige Validierung
2. **Gruppierung**: Gruppieren Sie zusammengehörige Einstellungen in `settings-section`-Divs
3. **Beschreibungen**: Nutzen Sie `<small class="form-text text-muted">` für Hilfstexte
4. **Fehlerbehandlung**: Nutzen Sie die vordefinierten Message-Blöcke
5. **Responsive Design**: Bootstrap-Grid-System für responsive Layouts verwenden

## Beispiel: Vollständige Integration

```python
# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi_app_settings.router import create_settings_router
from backend.database.base import get_db

app = FastAPI(title="Meine Anwendung")

# Statische Dateien (für eigene CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Settings-Router mit Templates
settings_router = create_settings_router(
    prefix="/api/settings",
    get_db=get_db,
    app_root=__file__.parent,
    extra_settings_file="app/config/extra_settings.py",
    enable_templates=True,
    templates_directory="templates/settings",
    custom_template_name="my_settings.html"
)

app.include_router(settings_router)
```

## Fehlerbehebung

### Template nicht gefunden

Fehler: `Template 'my_settings.html' not found`

Lösung:
- Überprüfen Sie den `templates_directory`-Pfad
- Stellen Sie sicher, dass die Template-Datei existiert
- Prüfen Sie die Logs für den initialisierten Template-Pfad

### Settings werden nicht angezeigt

Problem: `{{ settings.my_setting }}` ist leer

Lösung:
- Stellen Sie sicher, dass die Einstellung in `ALLOWED_SETTINGS` definiert ist
- Prüfen Sie, ob die Einstellung in der Datenbank existiert
- Verwenden Sie `{{ settings.my_setting | default('fallback') }}`

### Formular-Update funktioniert nicht

Problem: Änderungen werden nicht gespeichert

Lösung:
- Überprüfen Sie, dass `name`-Attribute in Input-Feldern gesetzt sind
- Stellen Sie sicher, dass die Einstellung nicht in `PROTECTED_SETTINGS` ist
- Prüfen Sie die Browser-Konsole und Server-Logs auf Fehler

## Erweiterte Anpassungen

### Eigene Nachrichten-Typen

```html
{% block messages %}
{{ super() }}  {# Behält die Standard-Nachrichten #}

{% if info_message %}
<div class="alert alert-info" role="alert">
    <strong>Info:</strong> {{ info_message }}
</div>
{% endif %}
{% endblock %}
```

### AJAX-Formular statt POST

```html
{% block form_submit_handler %}
e.preventDefault();
const formData = new FormData(this);
fetch('{{ form_action }}', {
    method: 'POST',
    body: formData
})
.then(response => response.text())
.then(html => {
    document.querySelector('.settings-container').innerHTML = html;
})
.catch(error => alert('Fehler: ' + error));
{% endblock %}
```

## Support

Bei Problemen oder Fragen:
1. Prüfen Sie die Logs: `logger.info` zeigt Template-Initialisierung
2. Aktivieren Sie Debug-Logging für detaillierte Informationen
3. Konsultieren Sie die Beispiel-Templates im Modul
