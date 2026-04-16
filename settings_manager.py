import logging
import importlib.util
import traceback
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Callable, Mapping
from pathlib import Path
import os

from sqlalchemy.orm import Session

try:
    from backend.app.config import settings as default_app_settings  # type: ignore
except Exception:  # pragma: no cover - optional for reusability
    default_app_settings = None  # type: ignore

from .models import (Setting,
                     ALLOWED_SETTINGS as BASE_ALLOWED,
                     PROTECTED_SETTINGS as BASE_PROTECTED,
                     READONLY_SETTINGS as BASE_READONLY)

# Configure logging
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SettingsManagerContext:
    """Context-Objekt, das Resolvern aus `EXTRA_SETTINGS_MAP` bereitgestellt wird."""

    app_root_path: Path | None
    manager: "SettingsManager"


def _dynamic_import_module(module_path: Path, module_name: str) -> Any | None:
    """Dynamischer Import eines Python-Moduls von Dateipfad.

    Analog zum Pattern in `router._dynamic_import_router`.
    """
    try:
        if not module_path.exists():
            logger.warning(f"Extra settings module file not found: {module_path}")
            return None
        spec = importlib.util.spec_from_file_location(module_name, str(module_path))
        if spec is None or spec.loader is None:
            logger.warning(f"Could not load spec for extra settings module: {module_path}")
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Failed to dynamically import module from {module_path}: {e}")
        traceback.print_exc()
        return None


class SettingsManager:
    """\
    Manager class for synchronizing ApplicationSettings and database-backed settings.
    Acts as the central interface for reading and writing settings.

    Reusability notes:
    - app_settings_obj can be injected (e.g., a Pydantic settings instance).
    - Without app_settings_obj only DB settings are managed (PROTECTED settings are ignored).
    """

    def __init__(self, db: Optional[Session] = None, app_settings_obj: Optional[Any] = None):
        self.db = db
        self._app_settings = app_settings_obj if app_settings_obj is not None else default_app_settings
        self._cached_db_settings: Dict[str, Any] = {}
        self._initialized = False
        # Combined setting lists (sets for easy union and case-insensitive comparisons)
        self._allowed_settings = {s.lower() for s in BASE_ALLOWED}
        self._protected_settings = {s.lower() for s in BASE_PROTECTED}
        self._readonly_settings = {s.lower() for s in BASE_READONLY}
        # App-specific default values (lowercased keys). Values may be constants or callables.
        self._default_settings_values: Dict[str, Any] = {}
        # App-specific resolver map (lowercased keys). Values are callables.
        self._extra_settings_map: Dict[str, Callable[[SettingsManagerContext], Any]] = {}
        # .env defaults (lowercased keys, string values)
        self._dotenv_values: Dict[str, str] = {}

        self._app_root_path = None
        self._bootstrap_settings: Optional[Dict[str, Any]] = None

    def set_app_settings(self, app_settings_obj: Optional[Any]) -> None:
        """Set/replace the ApplicationSettings instance."""
        self._app_settings = app_settings_obj

    def initialize(
        self,
        db: Session,
        app_root_path: Path,
        bootstrap_settings: Optional[Dict[str, Any]] = None,
        dotenv_path: Optional[object] = None,
        dotenv_override: bool = False,
    ) -> None:
        """\
        Initializes the SettingsManager with a DB session and syncs settings
        between ApplicationSettings and database.

        Optional: loads settings from a `.env` file and uses them as defaults.
        Parameters:
            db (Session): SQLAlchemy session object.
            app_root_path (Path): Absolute path to the app root.
            bootstrap_settings (Optional[Dict[str, Any]]): Dictionary of settings to bootstrap the settings manager with.
            dotenv_path (Optional[object]): Path to the `.env` file.
            dotenv_override (bool): Whether to override existing `.env` values with DB values.
        """
        self.db = db
        if not self._initialized:
            self._initialized = True

            # Set the absolute path of the app root
            self._app_root_path = app_root_path
            # Store the bootstrap settings (if any)
            self._bootstrap_settings = bootstrap_settings

            # Load .env first so ENV defaults are available during later reads
            self.load_dotenv(dotenv_path=dotenv_path, override=dotenv_override)

            # Optionally apply ENV values to the injected app settings (non-protected only)
            self._sync_env_to_app_settings()

            self._sync_settings_to_db()
            self._load_settings_from_db()
            self._santinize_setting_attributes()

    def load_dotenv(self, dotenv_path: Optional[object] = None, override: bool = False) -> None:
        """\
        Loads variables from a `.env` file and stores them as internal defaults.

        Requirements:
        - optional dependency `python-dotenv`. If not installed, this is silently skipped.

        Behavior:
        - Only keys contained in `ALLOWED_SETTINGS` are imported.
        - Keys are stored lowercased.
        - Values remain strings; type conversion is done when syncing into ApplicationSettings.
        """
        try:
            from dotenv import dotenv_values, load_dotenv  # type: ignore
        except Exception:  # pragma: no cover
            logger.info("python-dotenv not installed; skipping .env loading")
            return

        path: Optional[Path]
        if dotenv_path is None:
            candidate = Path.cwd() / ".env"
            path = candidate if candidate.exists() else None
        else:
            p = Path(str(dotenv_path))
            path = p if p.is_absolute() else (Path.cwd() / p)
            path = path.resolve()
            if not path.exists():
                logger.warning(f".env file not found: {path}")
                return

        if path is None:
            return

        # Load into os.environ (depending on override)
        load_dotenv(dotenv_path=str(path), override=override)

        # Read raw key-values from file
        raw = dotenv_values(str(path))
        loaded_count = 0
        for k, v in raw.items():
            if not k or v is None:
                continue
            key_l = k.lower()
            if key_l not in self._allowed_settings:
                continue
            if (not override) and (key_l in self._dotenv_values):
                continue
            self._dotenv_values[key_l] = str(v)
            loaded_count += 1

        # Make .env values available as defaults in get_setting()
        for k, v in self._dotenv_values.items():
            self._default_settings_values.setdefault(k, v)

        logger.info(f"Loaded .env settings from {path}. Count: {loaded_count}")

    def _sync_env_to_app_settings(self) -> None:
        """\
        Syncs `.env`/`os.environ` values into ApplicationSettings (only `ALLOWED_SETTINGS`,
        excluding `PROTECTED_SETTINGS`).

        Note: This is optional; if no app settings object exists, nothing happens.
        """
        if self._app_settings is None:
            return

        for name in self._allowed_settings:
            if name in self._protected_settings:
                continue

            env_key = name.upper()
            if env_key not in os.environ:
                continue

            if not hasattr(self._app_settings, env_key):
                continue

            raw_val = os.environ.get(env_key)
            if raw_val is None:
                continue

            try:
                current_value = getattr(self._app_settings, env_key)
                if callable(current_value):
                    continue

                if isinstance(current_value, bool):
                    new_value = str(raw_val).lower() in ("true", "1", "yes", "y")
                elif isinstance(current_value, int):
                    new_value = int(raw_val)
                elif isinstance(current_value, float):
                    new_value = float(raw_val)
                else:
                    new_value = str(raw_val)

                setattr(self._app_settings, env_key, new_value)
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"Error while syncing ENV to ApplicationSettings for {env_key}: {e}")

    def load_app_specific_settings(
        self,
        file_rel_path: str,
        app_root: Optional[object] = None,
        allowed_var_name: str = "ALLOWED_SETTINGS",
        protected_var_name: str = "PROTECTED_SETTINGS",
        readonly_var_name: str = "READONLY_SETTINGS",
        default_values_var_name: str = "DEFAULT_SETTINGS_VALUES",
        extra_settings_map_var_name: str = "EXTRA_SETTINGS_MAP",
    ) -> None:
        """\
        Loads additional ALLOWED/PROTECTED lists from a Python file relative to the app root
        and merges them with the base lists.

        The file should expose variables with lists (e.g. ALLOWED_SETTINGS, PROTECTED_SETTINGS)
        and can optionally provide DEFAULT_SETTINGS_VALUES.

        Extension:
        - If `EXTRA_SETTINGS_MAP` is present, it must be a dict[str, callable]. The callable
          will be used by `get_default_value()` to compute dynamic defaults.
        """
        try:
            base = Path(str(app_root)) if app_root else Path.cwd()
            target = (base / file_rel_path).resolve()
            if not target.exists():
                logger.warning(f"Extra settings file not found: {target}")
                return

            module = _dynamic_import_module(target, module_name="app_specific_settings")
            if module is None:
                return

            # Retrieve variables from the module
            extra_allowed = getattr(module, allowed_var_name, None)
            extra_protected = getattr(module, protected_var_name, None)
            extra_readonly = getattr(module, readonly_var_name, None)
            extra_defaults = getattr(module, default_values_var_name, None)
            extra_map = getattr(module, extra_settings_map_var_name, None)

            if extra_allowed:
                self._allowed_settings.update({str(s).lower() for s in extra_allowed})
            if extra_protected:
                self._protected_settings.update({str(s).lower() for s in extra_protected})
            if extra_readonly:
                self._readonly_settings.update({str(s).lower() for s in extra_readonly})
            if isinstance(extra_defaults, dict):
                # Merge defaults (lowercase keys); values can be constants or callables.
                for k, v in extra_defaults.items():
                    self._default_settings_values[str(k).lower()] = v

            if isinstance(extra_map, dict):
                merged = 0
                for k, v in extra_map.items():
                    if k is None:
                        continue
                    key_l = str(k).lower()
                    if not callable(v):
                        logger.warning(
                            f"Ignoring EXTRA_SETTINGS_MAP entry for '{key_l}': value is not callable"
                        )
                        continue
                    # Later definitions override earlier ones
                    self._extra_settings_map[key_l] = v
                    merged += 1

                logger.info(f"Loaded EXTRA_SETTINGS_MAP entries: {merged}")

            logger.info(
                f"Loaded app-specific settings from {target}. "
                f"Allowed settings: {len(self._allowed_settings)}, "
                f"Protected settings: {len(self._protected_settings)}, "
                f"Defaults setting values: {len(self._default_settings_values)}, "
                f"Extra settings map: {len(self._extra_settings_map)}"
            )
        except Exception as e:
            logger.error(f"Failed to load app-specific settings from {file_rel_path}: {e}")
            traceback.print_exc()

    def get_allowed_settings(self) -> list[str]:
        return sorted(self._allowed_settings)

    def get_protected_settings(self) -> list[str]:
        return sorted(self._protected_settings)

    def get_default_settings_values(self) -> Dict[str, Any]:
        """Return a copy of default values.

        Note: Values may be constants or callables. Callables are **not** evaluated here,
        but on demand via `get_default_value`.
        """
        return dict(self._default_settings_values)

    def _resolver_context(self) -> SettingsManagerContext:
        return SettingsManagerContext(app_root_path=self._app_root_path, manager=self)

    def _invoke_extra_settings_resolver(self, name: str, resolver: Callable[..., Any]) -> Any:
        try:
            return resolver(self._resolver_context())
        except TypeError:
            # Rückwärtskompatibilität für ältere Resolver ohne ctx-Parameter.
            return resolver()
        except Exception as e:  # pragma: no cover
            logger.error(f"Error while evaluating EXTRA_SETTINGS_MAP for setting '{name}': {e}")
            return None

    def get_default_value(self, name: str) -> Optional[Any]:
        """Return the default value for a setting.

        Priority order:
        1) `EXTRA_SETTINGS_MAP[name]` (callable called with a `SettingsManagerContext`)
        2) `DEFAULT_SETTINGS_VALUES[name]` (constant or callable with no args)

        If execution fails, the error is logged and `None` is returned.
        """
        key = name.lower()

        if key in self._extra_settings_map:
            resolver = self._extra_settings_map[key]
            return self._invoke_extra_settings_resolver(name, resolver)

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
        """\
        Synchronizes ApplicationSettings into the database.
        Security-relevant settings are NOT written to the DB.
        """
        if not self.db:
            logger.warning("No database connection available for SettingsManager")
            return

        if self._app_settings is None:
            # No app settings available: no env->db sync
            return

        # Write only ALLOWED_SETTINGS into the database
        for setting_name in self._allowed_settings:
            setting_name_lower = setting_name.lower()

            # Does the setting exist on the ApplicationSettings object?
            if hasattr(self._app_settings, setting_name_lower.upper()):
                app_setting_value = getattr(self._app_settings, setting_name_lower.upper())

                # Skip computed settings
                if callable(app_setting_value):
                    continue

                # Convert complex types to string
                if not isinstance(app_setting_value, (str, int, float, bool)):
                    if hasattr(app_setting_value, "__str__"):
                        app_setting_value = str(app_setting_value)
                    else:
                        continue

                # Store in DB if not present yet
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
        """\
        Loads all settings from the DB and updates ApplicationSettings
        as well as the internal cache.
        """
        if not self.db:
            logger.warning("No database connection available for SettingsManager")
            return

        db_rows = self.db.query(Setting).all()

        # Update cache
        self._cached_db_settings = {row.name: row.value for row in db_rows}

        if self._app_settings is None:
            # Without app settings object, there is nothing to write back
            return

        # Update ApplicationSettings from DB values (excluding PROTECTED_SETTINGS)
        for row in db_rows:
            if row.name.lower() in self._protected_settings:
                continue

            setting_name_upper = row.name.upper()
            if hasattr(self._app_settings, setting_name_upper):
                try:
                    current_value = getattr(self._app_settings, setting_name_upper)

                    if isinstance(current_value, bool):
                        new_value = row.value.lower() in ("true", "1", "yes", "y")
                    elif isinstance(current_value, int):
                        new_value = int(row.value)
                    elif isinstance(current_value, float):
                        new_value = float(row.value)
                    else:
                        new_value = row.value

                    setattr(self._app_settings, setting_name_upper, new_value)
                    logger.debug(f"ApplicationSettings updated: {setting_name_upper}={new_value}")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Error while updating setting {setting_name_upper}: {str(e)}")

    def _santinize_setting_attributes(self):
        """\
        Ensures `is_dynamic` and `is_protected` attributes are set correctly for settings in the DB.

        - PROTECTED_SETTINGS are marked as is_dynamic=False, is_protected=True
        - ALLOWED_SETTINGS are marked as is_dynamic=True, is_protected=False
        """
        # Retrieve existing settings from database
        existing_settings = self.db.query(Setting).all()

        # First, check and mark PROTECTED_SETTINGS accordingly
        for setting in existing_settings:
            if setting.name not in self._protected_settings:
                continue

            # If either flag isn't set (yet), apply defaults
            if setting.is_protected is None or setting.is_dynamic is None:
                setting.is_protected = True
                setting.is_dynamic = False

            # Persist changes
            self.db.add(setting)

        # Then check and mark ALLOWED_SETTINGS accordingly
        for setting in existing_settings:
            if setting.name not in self._allowed_settings:
                continue

            # If either flag isn't set (yet), apply defaults
            if setting.is_protected is None or setting.is_dynamic is None:
                setting.is_protected = False
                setting.is_dynamic = True

            # Persist changes
            self.db.add(setting)

        # Commit all changes to database
        self.db.commit()

    def get_setting(self, name: str, default: Optional[Any] = None) -> Any:
        """
        Returns the value of a setting.
        PROTECTED_SETTINGS are always read from ApplicationSettings.
        Parameters:
            name (str): Setting name.
            default (Optional[Any]): Default value to return if setting is not found.
        """
        logger.info(f"Reading setting '{name}' from database or ApplicationSettings")
        if name.lower() in self._protected_settings:
            logger.info(f"Reading protected setting '{name}' from ApplicationSettings")
            if self._app_settings is None:
                logger.warning(f"Protected setting can not be read: {name}, returning default value: {default}")
                return default
            attr_name = name.upper()
            if hasattr(self._app_settings, attr_name):
                logger.info(f"Reading protected setting '{name}' from ApplicationSettings as attribute: "
                            f"{getattr(self._app_settings, attr_name)}")
                return getattr(self._app_settings, attr_name)

            logger.info(f"Returning default value for protected setting '{name}': {default}")
            return default

        # Check extra settings map for setting with given name, if database and ApplicationSettings have "fallen through"
        logger.info(f"Extra settings map: {self._extra_settings_map}")
        if self._extra_settings_map is not None and name.lower() in self._extra_settings_map:
            logger.info(f"Reading setting '{name}' from extra settings map: "
                        f"{self._extra_settings_map[name.lower()]}")
            return self._invoke_extra_settings_resolver(name, self._extra_settings_map[name.lower()])
        else:
            logger.info(f"No setting with name '{name}' found in extra settings map.")

        attr_name = name.upper()
        if self._app_settings is not None and hasattr(self._app_settings, attr_name):
            logger.info(f"Reading setting '{name}' from ApplicationSettings as attribute")
            value = getattr(self._app_settings, attr_name)
            if callable(value):
                value = value()

            logger.info(f"Returning setting '{name}' from ApplicationSettings as attribute: {value}")
            return value

        if name in self._cached_db_settings:
            logger.info(f"Reading setting '{name}' from database cache")
            return self._cached_db_settings[name]

        if self.db:
            logger.info(f"Reading setting '{name}' from database")
            db_setting = self.db.query(Setting).filter_by(name=name).first()
            if db_setting:
                logger.info(f"Setting '{name}' found in database, with value: {db_setting.value}")
                self._cached_db_settings[name] = db_setting.value
                return db_setting.value

        # Check bootstrap settings for setting with given name, if database and ApplicationSettings have "fallen through"
        if self._bootstrap_settings is not None and name.lower() in self._bootstrap_settings:
            logger.info(f"Reading setting '{name}' from bootstrap settings: "
                        f"{self._bootstrap_settings[name.lower()]}")
            return self._bootstrap_settings[name.lower()]
        else:
            logger.info(f"No setting with name '{name}' found in bootstrap settings.")

        # Fall back to defaults provided by the settings manager (constants or callables)
        default_from_manager = self.get_default_value(name)
        logger.info(f"Returning value for setting '{name}' as provided by settings manager: {default_from_manager}")
        if default_from_manager is not None:
            return default_from_manager

        logger.warning(f"No value found for setting '{name}', returning default value: {default}")
        return default

    def set_setting(self, name: str, value: Any) -> bool:
        """\
        Sets a setting value in ApplicationSettings and the database.
        PROTECTED_SETTINGS cannot be set.

        Parameters:
            name: Setting name.
            value: Value to set.
        Returns:
            True on success, False on failure.
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
        """Returns all settings as a dictionary (DB + ApplicationSettings, only ALLOWED_SETTINGS)."""
        result: Dict[str, Any] = {}
        # First, all DB settings
        for name, value in self._cached_db_settings.items():
            if name.lower() in self._allowed_settings:
                result[name] = value

        if self._app_settings is not None:
            # Then ALLOWED settings from ApplicationSettings
            for attr in dir(self._app_settings):
                if not attr.startswith('_') and not callable(getattr(self._app_settings, attr)):
                    if attr.lower() in self._allowed_settings:
                        result[attr.lower()] = getattr(self._app_settings, attr)
        return result


# Singleton instance
settings_manager = SettingsManager()

