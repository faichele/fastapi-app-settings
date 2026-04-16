import datetime
import os
import pathlib
import logging
import importlib.util
from typing import Callable, Generator, Any, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Path as FPath, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from PIL import Image
from starlette.responses import JSONResponse

from .models import (
    Setting,
    SettingResponse,
    SettingUpdate,
)
from .settings_manager import settings_manager

# Use standard logging module to avoid dependencies on external logger managers
logger = logging.getLogger(__name__)


def _resolve_backend_get_db() -> Callable[[], Generator[Session, None, None]] | None:
    """Lädt optional die get_db-Dependency aus einer Host-App.

    Der Import erfolgt bewusst lazy, damit das Paket ohne Backend-Kopplung
    importierbar bleibt und keine Zirkelimporte auf Modulebene entstehen.
    """
    try:
        from backend.database.base import get_db as backend_get_db  # type: ignore

        return backend_get_db
    except Exception as e:  # pragma: no cover - optional fallback path
        logger.info(f"No backend get_db fallback available: {e}")
        return None


def _create_session_factory(database_url: Any) -> sessionmaker:
    if hasattr(database_url, "unicode_string"):
        database_url = database_url.unicode_string()
    engine = create_engine(str(database_url))
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _make_get_db_dependency(
    session_factory: Callable[[], Session],
) -> Callable[[], Generator[Session, None, None]]:
    def _get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    return _get_db


def _dynamic_import_router(module_path: Path, attr_name: str = "router") -> Any | None:
    try:
        if not module_path.exists():
            logger.warning(f"Custom settings router file not found: {module_path}")
            return None
        spec = importlib.util.spec_from_file_location("app_specific_router", str(module_path))
        if spec is None or spec.loader is None:
            logger.warning(f"Could not load spec for custom router: {module_path}")
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, attr_name, None)
    except Exception as e:
        logger.error(f"Failed to dynamically import router from {module_path}: {e}")
        return None


def create_settings_router(
    prefix: str = "/api/settings",
    get_db: Callable[[], Generator[Session, None, None]] | None = None,
    session_factory: Callable[[], Session] | None = None,
    database_url: Any | None = None,
    *,
    app_root: str | Path | None = None,
    extra_settings_file: str | None = None,
    extra_settings_allowed_var: str = "ALLOWED_SETTINGS",
    extra_settings_protected_var: str = "PROTECTED_SETTINGS",
    extra_settings_defaults_var: str = "DEFAULT_SETTINGS_VALUES",
    extra_router_file: str | None = None,
    extra_router_attr: str = "router",
    enable_templates: bool = False,
    templates_directory: str | Path | None = None,
    custom_template_name: str | None = None,
):
    """
    Creates a FastAPI APIRouter for managing application settings.
    Args:
        prefix: optional API prefix, default: "/api/settings"
        get_db: optional, dependency factory for DB sessions. Using get_db from database.base if not provided.
        session_factory: optional, zero-arg callable returning a SQLAlchemy Session.
            Used when no explicit get_db dependency is injected.
        database_url: optional, database URL for creating an internal SQLAlchemy session factory.
            Useful when this package is used standalone outside the backend application.
        app_root: optional, root directory of the FastAPI application. Used to resolve relative paths.
        extra_settings_file: optional, relative path to a Python file (from app_root) that provides
        additional ALLOWED/PROTECTED settings lists and default values. Lists are merged with the defaults.
        extra_router_file: optional, relative path to a Python file (from app_root) that provides a router instance
        (default attribute name 'router'). The router will be included in the settings router.
        enable_templates: if True, enables HTML template rendering for settings UI
        templates_directory: optional, custom templates directory. If None, uses package's built-in templates
        custom_template_name: optional, custom template file name to use instead of default
    """
    if get_db is not None:
        db_dependency = get_db
    elif session_factory is not None:
        db_dependency = _make_get_db_dependency(session_factory)
    elif database_url is not None:
        db_dependency = _make_get_db_dependency(_create_session_factory(database_url))
    else:
        db_dependency = _resolve_backend_get_db()

    if db_dependency is None:
        raise RuntimeError(
            "No database dependency available. Provide get_db, session_factory, "
            "or database_url, or use this package within a backend exposing backend.database.base.get_db."
        )

    base = Path(app_root) if app_root else Path.cwd()
    settings_manager._initialized = False
    settings_manager.db = None
    settings_manager._cached_db_settings = {}
    settings_manager._app_root_path = base

    # Setup Jinja2 templates if enabled
    templates = None
    if enable_templates:
        if templates_directory:
            # Use custom templates directory
            template_path = Path(templates_directory)
            if not template_path.is_absolute():
                template_path = (base / template_path).resolve()
        else:
            # Use package's built-in templates
            template_path = Path(__file__).parent / "templates"

        if template_path.exists():
            templates = Jinja2Templates(directory=str(template_path))
            logger.info(f"Initialized Jinja2Templates with directory: {template_path}")
        else:
            logger.warning(f"Templates directory not found: {template_path}")
            templates = None

    # Load app-specific settings from a Python file, if provided
    if extra_settings_file:
        try:
            logger.info(f"Loading app-specific settings from {extra_settings_file}")
            settings_manager.load_app_specific_settings(
                file_rel_path=extra_settings_file,
                app_root=base,
                allowed_var_name=extra_settings_allowed_var,
                protected_var_name=extra_settings_protected_var,
                default_values_var_name=extra_settings_defaults_var,
            )
        except Exception as e:
            logger.error(f"Failed to load extra settings file '{extra_settings_file}': {e}")

    router = APIRouter(prefix=prefix, tags=["settings"])

    # Optional: Include an extra router from a Python file, if provided
    if extra_router_file:
        base = Path(app_root) if app_root else Path.cwd()
        module_path = (base / extra_router_file).resolve()
        extra_router = _dynamic_import_router(module_path, attr_name=extra_router_attr)
        if extra_router is not None:
            try:
                router.include_router(extra_router)
                logger.info(f"Included extra settings router from {module_path}")
            except Exception as e:
                logger.error(f"Failed to include extra router from {module_path}: {e}")

    @router.get("/{name}", response_model=SettingResponse)
    async def get_setting(name: str = FPath(...), db: Session = Depends(db_dependency)):
        """
        Returns a setting by its name.
        If the setting does not exist, it will be created with a default value.
        If the setting is "image_directory", it will return the absolute path to the image directory.
        """
        # Initialize the SettingsManager, if not already initialized
        if not settings_manager._initialized:
            settings_manager.initialize(db=db,
                                        app_root_path=base)

        protected_set = set(settings_manager.get_protected_settings())

        if name.lower() in protected_set:
            raise HTTPException(
                status_code=403,
                detail=f"Protected setting '{name}' cannot be retrieved",
            )

        # Retrieve the setting value using the SettingsManager

        logger.info(f"Retrieving setting from settings_manager: '{name}'...")

        setting_id = -1
        setting_value = settings_manager.get_setting(name)
        setting_created_date = datetime.datetime.now(datetime.UTC)
        setting_updated_date = datetime.datetime.now(datetime.UTC)
        setting_is_protected = False
        setting_is_dynamic = True

        logger.info(f"Retrieved setting from settings_manager: '{name}' with value '{setting_value}'")

        # If the setting value is not found in the SettingsManager, query it from the database
        if setting_value is None:
            setting = db.query(Setting).filter_by(name=name).first()
            # If found in the database, return the value stored there
            if setting:
                setting_value = setting.value
                setting_created_date = setting.created_date
                setting_updated_date = setting.updated_date
                setting_is_dynamic = setting.is_dynamic
            else:
                # First use app-specific defaults if present
                app_default = settings_manager.get_default_value(name)
                if app_default is not None:
                    setting_value = app_default
                    setting_is_protected = (name in protected_set)
                    setting_is_dynamic = True
                    setting_created_date = datetime.datetime.now(datetime.UTC)
                    setting_updated_date = datetime.datetime.now(datetime.UTC)

                    settings_manager.set_setting(name, setting_value)
                    setting = db.query(Setting).filter_by(name=name).first()
                else:
                    # Fallback: internal default values, hard-coded or queried on the fly
                    extensions = Image.registered_extensions()
                    formats = {v: k for k, v in extensions.items()}
                    logger.info(f"Image formats supported by PIL: {len(formats)}")
                    for format_name in sorted(formats.keys()):
                        logger.info(f"{format_name}: {formats[format_name]}")
                    supported_extensions_str = ";".join(extensions.keys())

                    # TODO: Consolidate default_values - this is a mess
                    # TODO: Read default values from application specific settings file instead of hardcoding them here!

                    if settings_manager.get_default_settings_values():
                        default_values = settings_manager.get_default_settings_values()
                        if name in default_values:
                            setting_value = default_values[name]
                            setting_created_date = datetime.datetime.now(datetime.UTC)
                            setting_updated_date = datetime.datetime.now(datetime.UTC)
                            setting_is_dynamic = True
                            setting_is_protected = (name in protected_set)

                            settings_manager.set_setting(name, setting_value)
                            setting = db.query(Setting).filter_by(name=name).first()
                        else:
                            raise HTTPException(status_code=404,
                                                detail=f"Setting '{name}' not found (/api/settings/{name})")
                    else:
                        raise HTTPException(status_code=404, detail=f"Setting '{name}' not found (/api/settings/{name})")
        else:
            setting = db.query(Setting).filter_by(name=name).first()
            if not setting:
                settings_manager.set_setting(name, setting_value)
                setting = db.query(Setting).filter_by(name=name).first()
            if not setting:
                raise HTTPException(status_code=404, detail=f"Setting '{name}' not found after creation attempt")

            setting_id = setting.id
            setting_value = setting.value

        logger.info(f"Returning setting: '{name}' with value '{setting_value}': "
                    f"is_dynamic = {setting.is_dynamic}, is_protected = {setting.is_protected}")

        setting_response = SettingResponse(
            id=setting_id,
            name=name,
            value=setting_value,
            created_date=setting_created_date,
            updated_date=setting_updated_date,
            is_protected=setting_is_protected,
            is_dynamic=setting_is_dynamic,
        )

        logger.info(f"Returning setting_response: {setting_response}")

        return setting_response

    @router.put("/{name}", response_model=SettingResponse)
    async def update_setting(
        name: str = FPath(...),
        setting_update: SettingUpdate | None = None,
        db: Session = Depends(db_dependency),
    ):
        """
        Updates a setting by its name.
        If the setting does not exist, it will be created with the provided value.
        Protected settings cannot be updated.
        """
        # Initialize the SettingsManager, if not already initialized
        if not settings_manager._initialized:
            settings_manager.initialize(db=db,
                                        app_root_path=base)

        protected_set = set(settings_manager.get_protected_settings())
        allowed_set = set(settings_manager.get_allowed_settings())

        if name.lower() in protected_set:
            raise HTTPException(
                status_code=403,
                detail=f"Geschützte Einstellung '{name}' kann nicht aktualisiert werden",
            )
        if name.lower() not in allowed_set:
            raise HTTPException(
                status_code=400,
                detail=f"Unbekannte Einstellung '{name}' kann nicht aktualisiert werden",
            )

        # Update the setting value using the SettingsManager
        if setting_update is None:
            raise HTTPException(status_code=400, detail="No setting payload provided")
        success = settings_manager.set_setting(name, setting_update.value)

        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Fehler beim Aktualisieren der Einstellung '{name}'",
            )

        setting = db.query(Setting).filter_by(name=name).first()
        if not setting:
            raise HTTPException(status_code=404, detail=f"Seting '{name}' could not be found after update attempt")
        if setting_update.is_protected is not None:
            setting.is_protected = setting_update.is_protected
        if setting_update.is_dynamic is not None:
            setting.is_dynamic = setting_update.is_dynamic
        db.commit()
        db.refresh(setting)
        return setting

    @router.get("/", response_model=list[SettingResponse])
    async def get_all_settings(db: Session = Depends(db_dependency)):
        """
        Returns all settings that are stored in the database.
        Protected settings are not included in the response.
        """
        if not settings_manager._initialized:
            settings_manager.initialize(db=db,
                                        app_root_path=base)

        protected_set = set(settings_manager.get_protected_settings())
        db_settings = db.query(Setting).all()
        return [s for s in db_settings if s.name.lower() not in protected_set]

    # Template rendering endpoints (only added if templates are enabled)
    if templates is not None:
        @router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
        async def settings_ui(request: Request, db: Session = Depends(db_dependency)):
            """
            Renders the settings UI using the configured template.
            This endpoint provides a web interface for viewing and editing settings.
            """
            if not settings_manager._initialized:
                settings_manager.initialize(db=db,
                                            app_root_path=base)

            # Get all settings for rendering
            all_settings = settings_manager.get_all_settings()

            # Parse composite settings (e.g., thumbnail_size)
            if "thumbnail_size" in all_settings:
                try:
                    width, height = all_settings["thumbnail_size"].split(",")
                    all_settings["thumbnail_width"] = int(width.strip())
                    all_settings["thumbnail_height"] = int(height.strip())
                except (ValueError, AttributeError):
                    all_settings["thumbnail_width"] = 200
                    all_settings["thumbnail_height"] = 200

            # Determine which template to use
            template_name = custom_template_name or "settings_base.html"

            try:
                return templates.TemplateResponse(
                    template_name,
                    {
                        "request": request,
                        "settings": all_settings,
                        "form_action": f"{prefix}/ui/update",
                    }
                )
            except Exception as e:
                logger.error(f"Error rendering template '{template_name}': {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Fehler beim Rendern des Templates: {str(e)}"
                )

        @router.post("/ui/update", response_class=HTMLResponse, include_in_schema=False)
        async def update_settings_form(request: Request, db: Session = Depends(db_dependency)):
            """
            Handles form submissions from the settings UI.
            Updates multiple settings at once and re-renders the page with a success message.
            """
            if not settings_manager._initialized:
                settings_manager.initialize(db=db,
                                            app_root_path=base)

            try:
                # Parse form data
                form_data = await request.form()

                success_count = 0
                failed_settings = []

                # Update each setting from the form
                for name, value in form_data.items():
                    # Skip CSRF tokens or other non-setting fields
                    if name.startswith("_"):
                        continue

                    # Check if setting is allowed
                    if name.lower() not in settings_manager.get_allowed_settings():
                        continue

                    # Skip protected settings
                    if name.lower() in settings_manager.get_protected_settings():
                        continue

                    # Handle composite settings (e.g., thumbnail size)
                    if name in ["thumbnail_width", "thumbnail_height"]:
                        continue  # Will be handled together

                    success = settings_manager.set_setting(name, value)
                    if success:
                        success_count += 1
                    else:
                        failed_settings.append(name)

                # Handle composite thumbnail_size setting
                if "thumbnail_width" in form_data and "thumbnail_height" in form_data:
                    thumbnail_size = f"{form_data['thumbnail_width']},{form_data['thumbnail_height']}"
                    if settings_manager.set_setting("thumbnail_size", thumbnail_size):
                        success_count += 1

                # Get updated settings
                all_settings = settings_manager.get_all_settings()

                # Parse composite settings for display
                if "thumbnail_size" in all_settings:
                    try:
                        width, height = all_settings["thumbnail_size"].split(",")
                        all_settings["thumbnail_width"] = int(width.strip())
                        all_settings["thumbnail_height"] = int(height.strip())
                    except (ValueError, AttributeError):
                        pass

                # Prepare messages
                success_message = None
                error_message = None

                if success_count > 0:
                    success_message = f"{success_count} Einstellung(en) erfolgreich aktualisiert."

                if failed_settings:
                    error_message = f"Fehler beim Aktualisieren folgender Einstellungen: {', '.join(failed_settings)}"

                template_name = custom_template_name or "settings_base.html"

                return templates.TemplateResponse(
                    template_name,
                    {
                        "request": request,
                        "settings": all_settings,
                        "form_action": f"{prefix}/ui/update",
                        "success_message": success_message,
                        "error_message": error_message,
                    }
                )

            except Exception as e:
                logger.error(f"Error updating settings from form: {e}")
                # Try to render error page
                all_settings = settings_manager.get_all_settings()
                template_name = custom_template_name or "settings_base.html"

                return templates.TemplateResponse(
                    template_name,
                    {
                        "request": request,
                        "settings": all_settings,
                        "form_action": f"{prefix}/ui/update",
                        "error_message": f"Ein Fehler ist aufgetreten: {str(e)}",
                    }
                )

    return router
