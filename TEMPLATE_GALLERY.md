# Template-Galerie

Eine visuelle Übersicht der verfügbaren Templates und deren Features.

## 📐 settings_base.html

Das Basis-Template ist ein minimalistisches, erweiterbares Framework für Einstellungs-Formulare.

### Features

- **Responsives Design**: Bootstrap 5 Grid-System
- **Erweiterbar**: Viele überschreibbare Blöcke
- **Nachrichten-System**: Erfolgs-, Fehler- und Warnmeldungen
- **Formular-Handling**: Automatische POST-Verarbeitung
- **Minimalistisch**: Nur grundlegendes Styling, leicht anzupassen

### Struktur

```
┌─────────────────────────────────────────────┐
│  [Titel]                                    │
│  Beschreibung                               │
├─────────────────────────────────────────────┤
│  [Nachrichten - optional]                   │
├─────────────────────────────────────────────┤
│  ╔═══════════════════════════════════════╗ │
│  ║  FORMULAR (content Block)             ║ │
│  ║                                        ║ │
│  ║  Hier kommen Ihre Formularfelder      ║ │
│  ║                                        ║ │
│  ╚═══════════════════════════════════════╝ │
│  [Speichern] [Zurücksetzen]                │
└─────────────────────────────────────────────┘
```

### Verwendung

```html
{% extends "settings_base.html" %}

{% block content %}
<!-- Ihre Formularfelder hier -->
{% endblock %}
```

## 📋 settings_example.html

Ein vollständiges Beispiel-Template mit allen gängigen Einstellungstypen.

### Features

- **Mehrere Sektionen**: Logisch gruppierte Einstellungen
- **Verschiedene Input-Typen**: Text, Select, Number
- **Geschützte Felder**: Visuelle Kennzeichnung (gelber Hintergrund)
- **Hilfe-Texte**: Beschreibungen unter jedem Feld
- **Grid-Layout**: Mehrspaltige Layouts (z.B. Breite/Höhe)
- **Validierung**: JavaScript-basierte Formular-Validierung

### Sektionen

1. **Allgemeine Einstellungen**
   - Projektname (Text-Input)
   - Umgebung (Select: Development/Staging/Production)

2. **Verzeichnisse**
   - Bildverzeichnis (Text-Input)
   - Thumbnail-Verzeichnis (Text-Input)
   - Upload-Verzeichnis (Text-Input)

3. **Thumbnail-Einstellungen**
   - Breite & Höhe (Number-Input, nebeneinander)
   - Skalierungstyp (Select: Absolute/Relative)

4. **Geschützte Einstellungen**
   - Datenbank-Server (Read-only, deaktiviert)

### Struktur

```
┌─────────────────────────────────────────────┐
│  Beispiel: Anwendungseinstellungen          │
│  Dies ist ein Beispiel-Template...          │
├─────────────────────────────────────────────┤
│  ┌─────────────────────────────────────┐   │
│  │ Allgemeine Einstellungen            │   │
│  │ • Projektname     [_____________]   │   │
│  │ • Umgebung        [v Development]   │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │ Verzeichnisse                       │   │
│  │ • Bildverzeichnis [_____________]   │   │
│  │ • Thumbnail-Dir   [_____________]   │   │
│  │ • Upload-Dir      [_____________]   │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │ Thumbnail-Einstellungen             │   │
│  │ • Breite  [200]    Höhe [200]       │   │
│  │ • Typ     [v Absolute Größe]        │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │ ⚠ Geschützte Einstellungen          │   │
│  │ • DB-Server [localhost] (disabled)  │   │
│  └─────────────────────────────────────┘   │
│  [Speichern] [Zurücksetzen]                │
└─────────────────────────────────────────────┘
```

## 🎨 Styling-Guide

### CSS-Klassen

| Klasse | Verwendung |
|--------|-----------|
| `.settings-container` | Hauptcontainer |
| `.settings-header` | Kopfbereich mit Titel |
| `.settings-section` | Gruppierung von Einstellungen |
| `.form-group` | Einzelnes Formularfeld |
| `.form-label` | Label für Input-Felder |
| `.form-control` | Input/Select-Felder |
| `.protected-setting` | Geschützte/Read-only Einstellungen |
| `.alert-custom` | Nachrichten (Erfolg/Fehler) |

### Farben

- **Primär**: Bootstrap Primary (#0d6efd)
- **Hintergrund**: Light Gray (#f8f9fa)
- **Container**: White (#ffffff)
- **Border**: Gray (#dee2e6)
- **Geschützt**: Warning Yellow (#fff3cd)

### Responsive Breakpoints

- **Mobile**: < 576px (1 Spalte)
- **Tablet**: 576px - 768px (1-2 Spalten)
- **Desktop**: > 768px (bis zu 12-Spalten Bootstrap Grid)

## 🔧 Anpassungsbeispiele

### Beispiel 1: Dunkles Theme

```html
{% extends "settings_base.html" %}

{% block extra_styles %}
body {
    background-color: #1a1a1a;
    color: #e0e0e0;
}
.settings-container {
    background-color: #2d2d2d;
    border: 1px solid #444;
}
.form-control, .form-select {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border-color: #555;
}
{% endblock %}
```

### Beispiel 2: Kompaktes Layout

```html
{% extends "settings_base.html" %}

{% block extra_styles %}
.settings-container {
    max-width: 800px;
    padding: 20px;
}
.form-group {
    margin-bottom: 10px;
}
.settings-section h3 {
    font-size: 1.2rem;
    margin-bottom: 10px;
}
{% endblock %}
```

### Beispiel 3: Tabs für Sektionen

```html
{% extends "settings_base.html" %}

{% block content %}
<ul class="nav nav-tabs" role="tablist">
    <li class="nav-item">
        <a class="nav-link active" data-bs-toggle="tab" href="#general">Allgemein</a>
    </li>
    <li class="nav-item">
        <a class="nav-link" data-bs-toggle="tab" href="#advanced">Erweitert</a>
    </li>
</ul>

<div class="tab-content mt-3">
    <div id="general" class="tab-pane fade show active">
        <!-- Allgemeine Einstellungen -->
    </div>
    <div id="advanced" class="tab-pane fade">
        <!-- Erweiterte Einstellungen -->
    </div>
</div>
{% endblock %}
```

## 📱 Responsives Verhalten

### Mobile (< 576px)
- Einspaltige Ansicht
- Volle Breite für alle Inputs
- Gestapelte Buttons
- Touch-optimierte Größen

### Tablet (576px - 992px)
- Ein- bis zweispaltig (je nach Grid)
- Optimierte Button-Größen
- Kompaktere Abstände

### Desktop (> 992px)
- Mehrspaltige Layouts möglich
- Seitliche Margins
- Optimale Lesbarkeit

## 🎯 Best Practices

### 1. Sektionierung
Gruppieren Sie zusammengehörige Einstellungen in `.settings-section` Divs:

```html
<div class="settings-section">
    <h3>Kategorie-Name</h3>
    <!-- Einstellungen hier -->
</div>
```

### 2. Hilfe-Texte
Verwenden Sie `<small class="form-text text-muted">` für Beschreibungen:

```html
<input type="text" ...>
<small class="form-text text-muted">Erklärung des Feldes</small>
```

### 3. Geschützte Felder
Markieren Sie Read-only Einstellungen visuell:

```html
<div class="settings-section protected-setting">
    <h3>Geschützte Einstellungen</h3>
    <input ... disabled readonly>
</div>
```

### 4. Validierung
Fügen Sie clientseitige Validierung hinzu:

```html
{% block extra_scripts %}
<script>
document.getElementById('settingsForm').addEventListener('submit', function(e) {
    // Validierungslogik
});
</script>
{% endblock %}
```

## 🔍 Template-Debugging

### Variablen inspizieren

```html
{% block content %}
<pre>{{ settings | tojson(indent=2) }}</pre>
{% endblock %}
```

### Verfügbare Variablen

```html
<!-- In jedem Template verfügbar -->
{{ request }}         <!-- FastAPI Request-Objekt -->
{{ settings }}        <!-- Dict aller Einstellungen -->
{{ form_action }}     <!-- Submit-URL -->
{{ success_message }} <!-- Nach erfolgreichem Update -->
{{ error_message }}   <!-- Bei Fehler -->
```

## 📚 Weitere Ressourcen

- **Bootstrap 5 Docs**: https://getbootstrap.com/docs/5.3/
- **Jinja2 Docs**: https://jinja.palletsprojects.com/
- **HTML Forms**: https://developer.mozilla.org/de/docs/Learn/Forms

## 💡 Tipps & Tricks

1. **Nutzen Sie Bootstrap-Komponenten**: Cards, Badges, Alerts, etc.
2. **AJAX für bessere UX**: Formulare ohne Seitenreload
3. **Icons**: Font Awesome oder Bootstrap Icons
4. **Tooltips**: Für zusätzliche Informationen
5. **Modal-Dialoge**: Für Bestätigungen oder erweiterte Optionen
