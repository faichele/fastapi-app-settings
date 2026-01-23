# Templates - README

Dieses Verzeichnis enthält die Jinja2-Templates für die Settings-UI.

## 📁 Inhalt

- **settings_base.html** - Basis-Template (Rahmen für eigene Formulare)
- **settings_example.html** - Vollständiges Beispiel mit allen Features

## 🚀 Verwendung

### Option 1: Basis-Template

Erstellen Sie Ihr eigenes Template, das `settings_base.html` erweitert:

```html
{% extends "settings_base.html" %}

{% block title %}Meine Einstellungen{% endblock %}

{% block content %}
<div class="settings-section">
    <h3>Meine Einstellungen</h3>
    
    <div class="form-group">
        <label for="setting_name" class="form-label">Einstellungsname</label>
        <input type="text" class="form-control" 
               name="setting_name" 
               value="{{ settings.setting_name | default('') }}">
    </div>
</div>
{% endblock %}
```

### Option 2: Beispiel-Template

Verwenden Sie das Beispiel-Template direkt oder als Vorlage:

```python
from fastapi_app_settings import create_settings_router

router = create_settings_router(
    enable_templates=True,
    custom_template_name="settings_example.html"
)
```

## 🎨 Template-Struktur

### settings_base.html

**Überschreibbare Blöcke:**

| Block | Beschreibung |
|-------|--------------|
| `title` | Browser-Tab Titel |
| `page_title` | Hauptüberschrift auf der Seite |
| `page_description` | Beschreibungstext |
| `content` | Hauptinhalt (Ihre Formularfelder) |
| `extra_head` | Zusätzliche Head-Inhalte |
| `extra_styles` | Eigene CSS-Styles |
| `messages` | Nachrichten (Erfolg/Fehler/Warnung) |
| `form_action` | Submit-URL |
| `form_buttons` | Formular-Buttons |
| `extra_scripts` | Eigene JavaScript-Scripts |
| `form_submit_handler` | JavaScript Submit-Handler |

**Verfügbare Variablen:**

- `request` - FastAPI Request-Objekt
- `settings` - Dictionary aller Einstellungen
- `form_action` - URL für Formular-Submit
- `success_message` - Erfolgsmeldung (nach Update)
- `error_message` - Fehlermeldung
- `warning_message` - Warnmeldung

### settings_example.html

Zeigt alle Features:
- Mehrere Sektionen
- Verschiedene Input-Typen (Text, Select, Number)
- Grid-Layout (mehrspaltig)
- Geschützte Einstellungen
- Validierung

## 📝 Beispiele

### Einfaches Template

```html
{% extends "settings_base.html" %}

{% block content %}
<div class="settings-section">
    <div class="form-group">
        <label for="project_name" class="form-label">Projektname</label>
        <input type="text" class="form-control" 
               name="project_name" 
               value="{{ settings.project_name | default('') }}">
    </div>
</div>
{% endblock %}
```

### Mit Validierung

```html
{% extends "settings_base.html" %}

{% block content %}
<!-- Ihre Felder hier -->
{% endblock %}

{% block extra_scripts %}
<script>
document.getElementById('settingsForm').addEventListener('submit', function(e) {
    const value = document.getElementById('project_name').value;
    if (value.length < 3) {
        e.preventDefault();
        alert('Mindestens 3 Zeichen erforderlich!');
    }
});
</script>
{% endblock %}
```

### Mit eigenem Styling

```html
{% extends "settings_base.html" %}

{% block extra_styles %}
.settings-container {
    background: linear-gradient(to bottom, #f0f0f0, #ffffff);
}
.settings-section {
    border-left: 4px solid #007bff;
    padding-left: 20px;
}
{% endblock %}

{% block content %}
<!-- Ihre Felder hier -->
{% endblock %}
```

## 🎨 Styling

Die Templates verwenden Bootstrap 5 für grundlegendes Styling.

**CSS-Klassen:**

- `.settings-container` - Hauptcontainer
- `.settings-header` - Kopfbereich
- `.settings-section` - Sektion mit gruppierten Einstellungen
- `.form-group` - Einzelnes Formularfeld
- `.form-label` - Label
- `.form-control` - Input-Feld
- `.form-select` - Select-Feld
- `.protected-setting` - Geschützte Einstellungen (gelber Hintergrund)
- `.alert-custom` - Benachrichtigungen

## 🔧 Anpassung

### Eigenes CSS einbinden

```html
{% block extra_head %}
<link rel="stylesheet" href="/static/css/my-settings.css">
{% endblock %}
```

### Eigenes JavaScript einbinden

```html
{% block extra_scripts %}
<script src="/static/js/my-settings.js"></script>
{% endblock %}
```

### Bootstrap ersetzen

Wenn Sie kein Bootstrap verwenden möchten:

```html
{% extends "settings_base.html" %}

{% block extra_head %}
<!-- Entfernen Sie Bootstrap -->
<style>
/* Ihr eigenes CSS */
</style>
{% endblock %}
```

## 📱 Responsive Design

Die Templates sind responsive und funktionieren auf:
- Desktop (> 992px)
- Tablet (576px - 992px)
- Mobile (< 576px)

## 🔒 Sicherheit

**Geschützte Einstellungen:**

Einstellungen in `PROTECTED_SETTINGS` werden automatisch nicht über das Formular aktualisiert.

Um sie anzuzeigen (aber nicht editierbar):

```html
<div class="settings-section protected-setting">
    <h3>Geschützte Einstellungen</h3>
    <input type="text" class="form-control" 
           value="{{ settings.api_key | default('***') }}" 
           disabled readonly>
</div>
```

## 📚 Weitere Informationen

- **Vollständige Dokumentation**: `../TEMPLATE_USAGE.md`
- **Schnellstart**: `../QUICKSTART.md`
- **Beispiele**: `../example_template_usage.py`
- **Jinja2 Dokumentation**: https://jinja.palletsprojects.com/

## 💡 Tipps

1. **Starten Sie mit dem Beispiel**: Kopieren Sie `settings_example.html` und passen Sie es an
2. **Nutzen Sie Blöcke**: Überschreiben Sie nur die Blöcke, die Sie ändern möchten
3. **Testen Sie responsiv**: Öffnen Sie die Browser-Entwicklertools
4. **Validieren Sie**: Fügen Sie clientseitige Validierung hinzu
5. **Gruppieren Sie**: Nutzen Sie `.settings-section` für logische Gruppierungen

## 🐛 Debugging

**Template-Variablen anzeigen:**

```html
{% block content %}
<pre>{{ settings | tojson(indent=2) }}</pre>
{% endblock %}
```

**Alle verfügbaren Variablen:**

```html
<pre>
Request: {{ request }}
Settings: {{ settings }}
Form Action: {{ form_action }}
</pre>
```

## ✨ Erweiterte Features

### Tabs für Sektionen

```html
{% block content %}
<ul class="nav nav-tabs" role="tablist">
    <li class="nav-item">
        <a class="nav-link active" data-bs-toggle="tab" href="#tab1">Tab 1</a>
    </li>
</ul>
<div class="tab-content">
    <div id="tab1" class="tab-pane fade show active">
        <!-- Inhalt -->
    </div>
</div>
{% endblock %}
```

### Modal-Dialoge

```html
{% block extra_scripts %}
<script>
function confirmChange() {
    return confirm('Sind Sie sicher?');
}
document.getElementById('settingsForm').onsubmit = confirmChange;
</script>
{% endblock %}
```

### AJAX-Submission

```html
{% block form_submit_handler %}
e.preventDefault();
fetch('{{ form_action }}', {
    method: 'POST',
    body: new FormData(this)
}).then(response => response.text())
  .then(html => {
    // Aktualisiere UI
  });
{% endblock %}
```

---

**Viel Erfolg beim Erstellen Ihrer Settings-UI! 🎉**
