import logging
import importlib.util
import traceback
from typing import Any, Dict, Iterable
from pathlib import Path
from sqlalchemy.orm import Session

try:
    from backend.app.config import settings as default_app_settings  # type: ignore
except Exception:  # pragma: no cover - optional for reusability
    default_app_settings = None  # type: ignore

from .models import Setting, ALLOWED_SETTINGS as BASE_ALLOWED, PROTECTED_SETTINGS as BASE_PROTECTED

# Configure logging
logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Manager-Klasse zur Synchronisierung von ApplicationSettings und Datenbank-Settings.
    Dient als zentrale Schnittstelle zum Lesen und Schreiben von Einstellungen.

    Hinweise zur Wiederverwendbarkeit:
    - app_settings_obj kann optional injiziert werden (z. B. Pydantic Settings-Instanz).
    - Ohne app_settings_obj werden nur DB-Settings verwaltet (PROTECTED werden ignoriert).
    """

    def __init__(self, db: Session | None = None, app_settings_obj: Any | None = None):
        self.db = db
        self._app_settings = app_settings_obj if app_settings_obj is not None else default_app_settings
        self._cached_db_settings: Dict[str, Any] = {}
        self._initialized = False
        # Kombinierte Settingslisten (Sets für einfache Vereinigung und Case-insensitive Vergleiche)
        self._allowed_settings = {s.lower() for s in BASE_ALLOWED}
        self._protected_settings = {s.lower() for s in BASE_PROTECTED}
        # App-spezifische Defaultwerte (lowercased Keys). Werte können Konstanten oder Callables sein.
        self._default_settings_values: Dict[str, Any] = {}

    def set_app_settings(self, app_settings_obj: Any | None) -> None:
        """
        Enables setting/replacing the ApplicationSettings instance.
        """
        self._app_settings = app_settings_obj

    def initialize(self, db: Session) -> None:
        """
        Initializes the SettingsManager with a db session and syncs settings
        between ApplicationSettings and database
        """
        self.db = db
        if not self._initialized:
            self._initialized = True
            self._sync_settings_to_db()
            self._load_settings_from_db()
            self._santinize_setting_attributes()

    def load_app_specific_settings(
        self,
        file_rel_path: str,
        app_root: str | Path | None = None,
        allowed_var_name: str = "ALLOWED_SETTINGS",
        protected_var_name: str = "PROTECTED_SETTINGS",
        default_values_var_name: str = "DEFAULT_SETTINGS_VALUES",
    ) -> None:
        """
        Lädt zusätzliche ALLOWED/PROTECTED-Listen aus einer Python-Datei relativ zum App-Root
        und vereinigt sie mit den Basislisten.
        Die Datei sollte Variablen mit Listen beinhalten (z. B. ALLOWED_SETTINGS, PROTECTED_SETTINGS).
        """
        try:
            base = Path(app_root) if app_root else Path.cwd()
            target = (base / file_rel_path).resolve()
            if not target.exists():
                logger.warning(f"Extra settings file not found: {target}")
                return

            spec = importlib.util.spec_from_file_location("app_specific_settings", str(target))
            if spec is None or spec.loader is None:
                logger.warning(f"Could not load spec for extra settings file: {target}")
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Aus Modul die Variablen lesen
            extra_allowed: Iterable[str] | None = getattr(module, allowed_var_name, None)
            extra_protected: Iterable[str] | None = getattr(module, protected_var_name, None)
            extra_defaults: Dict[str, Any] | None = getattr(module, default_values_var_name, None)

            if extra_allowed:
                self._allowed_settings.update({s.lower() for s in extra_allowed})
            if extra_protected:
                self._protected_settings.update({s.lower() for s in extra_protected})
            if isinstance(extra_defaults, dict):
                # Merge defaults (lowercase keys); Werte können Konstanten oder Callables sein.
                for k, v in extra_defaults.items():
                    self._default_settings_values[k.lower()] = v

            logger.info(
                f"Loaded app-specific settings from {target}. Allowed: {len(self._allowed_settings)}, Protected: {len(self._protected_settings)}, Defaults: {len(self._default_settings_values)}"
            )
        except Exception as e:
            logger.error(f"Failed to load app-specific settings from {file_rel_path}: {e}")
            traceback.print_exc()

    def get_allowed_settings(self) -> list[str]:
        return sorted(self._allowed_settings)

    def get_protected_settings(self) -> list[str]:
        return sorted(self._protected_settings)

    def get_default_settings_values(self) -> Dict[str, Any]:
        """Gibt eine Kopie der Default-Werte zurück.

        Hinweis: Enthaltene Werte können Konstanten oder Callables sein. Callables werden
        hier **nicht** ausgewertet, sondern erst bei Bedarf über `get_default_value`.
        """
        return dict(self._default_settings_values)

    def get_default_value(self, name: str) -> Any | None:
        """Gibt den Default-Wert für ein Setting zurück.

        Unterstützt sowohl konstante Werte als auch Callables in DEFAULT_SETTINGS_VALUES.
        Bei Callables wird die Funktion beim Zugriff ausgeführt. Tritt dabei ein Fehler auf,
        wird dieser geloggt und `None` zurückgegeben.
        """
        key = name.lower()
        if key not in self._default_settings_values:
            return None

        value = self._default_settings_values[key]
        if callable(value):
            try:
                return value()
            except Exception as e:  # pragma: no cover - defensive programming
                logger.error(f"Error while evaluating default for setting '{name}': {e}")
                return None
        return value

    def _sync_settings_to_db(self) -> None:
        """
        Synchronisiert ApplicationSettings mit der Datenbank.
        Sicherheitsrelevante Settings werden NICHT in die DB geschrieben.
        """
        if not self.db:
            logger.warning("No database connection available for SettingsManager")
            return

        if self._app_settings is None:
            # Keine App-Settings vorhanden: keine Synchronisation aus ENV
            return

        # Nur ALLOWED_SETTINGS in die DB schreiben
        for setting_name in self._allowed_settings:
            setting_name_lower = setting_name.lower()

            # Existiert das Setting in den ApplicationSettings?
            if hasattr(self._app_settings, setting_name_lower.upper()):
                app_setting_value = getattr(self._app_settings, setting_name_lower.upper())

                # Berechnete Settings überspringen
                if callable(app_setting_value):
                    continue

                # Komplexe Typen in String konvertieren
                if not isinstance(app_setting_value, (str, int, float, bool)):
                    if hasattr(app_setting_value, "__str__"):
                        app_setting_value = str(app_setting_value)
                    else:
                        continue

                # In DB speichern, falls noch nicht vorhanden
                db_setting = self.db.query(Setting).filter_by(name=setting_name).first()

                if not db_setting:
                    logger.info(f"Creating new setting in database: {setting_name}={app_setting_value}")
                    db_setting = Setting(
                        name=setting_name,
                        value=str(app_setting_value),
                        is_protected=setting_name_lower in self._protected_settings,
                        is_dynamic=True,
                    )
                    self.db.add(db_setting)
                    self.db.commit()

    def _load_settings_from_db(self) -> None:
        """
        Lädt alle Settings aus der DB und aktualisiert ApplicationSettings
        sowie den internen Cache.
        """
        if not self.db:
            logger.warning("No database connection available for SettingsManager")
            return

        db_settings = self.db.query(Setting).all()

        # Cache aktualisieren
        self._cached_db_settings = {setting.name: setting.value for setting in db_settings}

        if self._app_settings is None:
            # Ohne App-Settings keine Rückspielung in ENV
            return

        # ApplicationSettings mit DB-Werten aktualisieren (ohne PROTECTED_SETTINGS)
        for setting in db_settings:
            if setting.name.lower() in self._protected_settings:
                continue

            setting_name_upper = setting.name.upper()
            if hasattr(self._app_settings, setting_name_upper):
                try:
                    current_value = getattr(self._app_settings, setting_name_upper)

                    if isinstance(current_value, bool):
                        new_value = setting.value.lower() in ("true", "1", "yes", "y")
                    elif isinstance(current_value, int):
                        new_value = int(setting.value)
                    elif isinstance(current_value, float):
                        new_value = float(setting.value)
                    else:
                        new_value = setting.value

                    setattr(self._app_settings, setting_name_upper, new_value)
                    logger.debug(f"ApplicationSettings updated: {setting_name_upper}={new_value}")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Error while updating setting {setting_name_upper}: {str(e)}")

    def _santinize_setting_attributes(self):
        """
        Set is_dynamic and is_protected attributes for settings in database.
        * PROTECTED_SETTINGS are marked as is_dynamic=False, is_protected=True
        * ALLOWED_SETTINGS are marked as is_dynamic=True, is_protected=False
        :return:
        """
        # Retrieve existing settings from database
        existing_settings = self.db.query(Setting).all()

        # First check and mark PROTECTED_SETTINGS accordingly
        for setting in existing_settings:
            if setting.name not in self._protected_settings:
                continue

            # If one of is_protected or is_dynamic is not set (yet), apply default values
            if setting.is_protected is None or setting.is_dynamic is None:
                setting.is_protected = True
                setting.is_dynamic = False

            # Commit changes to database record
            self.db.add(setting)

        # Then check and mank ALLOWED_SETTINGS accordingly
        for setting in existing_settings:
            if setting.name not in self._allowed_settings:
                continue

            # If one of is_protected or is_dynamic is not set (yet), apply default values
            if setting.is_protected is None or setting.is_dynamic is None:
                setting.is_protected = False
                setting.is_dynamic = True

            # Commit changes to database record
            self.db.add(setting)

        # Commit all changes to database
        self.db.commit()


    def get_setting(self, name: str, default: Any | None = None) -> Any:
        """
        Liefert den Wert eines Settings.
        PROTECTED_SETTINGS werden immer aus den ApplicationSettings gelesen.
        """
        if name.lower() in self._protected_settings:
            if self._app_settings is None:
                return default
            attr_name = name.upper()
            if hasattr(self._app_settings, attr_name):
                return getattr(self._app_settings, attr_name)
            return default

        attr_name = name.upper()
        if self._app_settings is not None and hasattr(self._app_settings, attr_name):
            value = getattr(self._app_settings, attr_name)
            if callable(value):
                value = value()
            return value

        if name in self._cached_db_settings:
            return self._cached_db_settings[name]

        if self.db:
            db_setting = self.db.query(Setting).filter_by(name=name).first()
            if db_setting:
                self._cached_db_settings[name] = db_setting.value
                return db_setting.value

        # Fallback to provided default values (constant or callables)
        default_from_manager = self.get_default_value(name)
        if default_from_manager is not None:
            return default_from_manager

        return default

    def set_setting(self, name: str, value: Any) -> bool:
        """
        Sets a setting value in ApplicationSettings and the database.
        PROTECTED_SETTINGS can not be set.
        Parameters:
            name (str): Name of the setting.
            value (Any): Value to set.
        Returns:
            bool - True on success, False on failure
        """
        if not self.db:
            logger.warning("No database connection available for SettingsManager")
            return False

        if name.lower() in self._protected_settings:
            logger.warning(f"Protected setting can not be updated: {name}")
            return False

        db_setting = self.db.query(Setting).filter_by(name=name).first()

        if db_setting:
            db_setting.value = str(value)
        else:
            if name.lower() not in self._allowed_settings:
                logger.warning(f"Unknown setting can not be set or updated: {name}")
                return False
            db_setting = Setting(
                name=name,
                value=str(value),
                is_dynamic=True,
            )
            self.db.add(db_setting)

        try:
            self.db.commit()
            self._cached_db_settings[name] = str(value)

            if self._app_settings is not None:
                attr_name = name.upper()
                if hasattr(self._app_settings, attr_name):
                    current_value = getattr(self._app_settings, attr_name)
                    if isinstance(current_value, bool):
                        new_value = str(value).lower() in ("true", "1", "yes", "y")
                    elif isinstance(current_value, int):
                        new_value = int(value)
                    elif isinstance(current_value, float):
                        new_value = float(value)
                    else:
                        new_value = str(value)
                    setattr(self._app_settings, attr_name, new_value)

            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error occurred while setting Setting {name}: {str(e)}")
            return False

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Liefert alle Settings als Dictionary (DB + ApplicationSettings, nur ALLOWED_SETTINGS).
        """
        result: Dict[str, Any] = {}
        # Zuerst alle DB-Settings
        for name, value in self._cached_db_settings.items():
            result[name] = value

        if self._app_settings is not None:
            # Dann ALLOWED aus ApplicationSettings
            for attr in dir(self._app_settings):
                if not attr.startswith('_') and not callable(getattr(self._app_settings, attr)):
                    if attr.lower() in self._allowed_settings:
                        result[attr.lower()] = getattr(self._app_settings, attr)
        return result


# Singleton instance
settings_manager = SettingsManager()
