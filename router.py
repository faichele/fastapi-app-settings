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
from sqlalchemy.orm import Session
from PIL import Image
from starlette.responses import JSONResponse

try:
    from backend.database.base import get_db as default_get_db  # type: ignore
except Exception:  # pragma: no cover
    default_get_db = None  # type: ignore

from .models import (
    Setting,
    SettingResponse,
    SettingUpdate,
)
from .settings_manager import settings_manager

# Use standard logging module to avoid dependencies on external logger managers
logger = logging.getLogger(__name__)


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
        app_root: optional, root directory of the FastAPI application. Used to resolve relative paths.
        extra_settings_file: optional, relative path to a Python file (from app_root) that provides
        additional ALLOWED/PROTECTED settings lists and default values. Lists are merged with the defaults.
        extra_router_file: optional, relative path to a Python file (from app_root) that provides a router instance
        (default attribute name 'router'). The router will be included in the settings router.
        enable_templates: if True, enables HTML template rendering for settings UI
        templates_directory: optional, custom templates directory. If None, uses package's built-in templates
        custom_template_name: optional, custom template file name to use instead of default
    """
    db_dependency = get_db if get_db is not None else default_get_db
    if db_dependency is None:
        raise RuntimeError("No get_db dependency provided and backend.database.base.get_db not available")

    # Setup Jinja2 templates if enabled
    templates = None
    if enable_templates:
        if templates_directory:
            # Use custom templates directory
            template_path = Path(templates_directory)
            if not template_path.is_absolute():
                base = Path(app_root) if app_root else Path.cwd()
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
            base = Path(app_root) if app_root else Path.cwd()
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
            settings_manager.initialize(db)

        protected_set = set(settings_manager.get_protected_settings())

        if name.lower() in protected_set:
            raise HTTPException(
                status_code=403,
                detail=f"Protected setting '{name}' cannot be retrieved",
            )

        # Retrieve the setting value using the SettingsManager
        setting_id = -1
        setting_value = settings_manager.get_setting(name)
        setting_created_date = datetime.datetime.now(datetime.UTC)
        setting_updated_date = datetime.datetime.now(datetime.UTC)
        setting_is_protected = False
        setting_is_dynamic = True

        # If the setting value is not found in the SettingsManager, query it from the database
        if setting_value is None:
            setting = db.query(Setting).filter_by(name=name).first()
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
                    default_values = {
                        "image_directory": "static/images",
                        "absolute_image_directory": "static/images",
                        "thumbnail_size": "200,200",
                        "thumbnail_size_type": "absolute",
                        # TODO: One alias for supported image formats instead of three!
                        "formats": supported_extensions_str,
                        "supported_formats": supported_extensions_str,
                        "supported_image_formats": supported_extensions_str,
                        "upload": "static/uploads",
                        "upload_directory": "static/uploads",
                        "absolute_upload_directory": "static/uploads",
                        "thumbnails": "static/thumbnails",
                        "thumbnail_directory": "static/thumbnails",
                        "absolute_thumbnail_directory": "static/thumb",
                        "default-album": 1,
                    }
                    if name in default_values:
                        setting_value = default_values[name]
                        setting_created_date = datetime.datetime.now(datetime.UTC)
                        setting_updated_date = datetime.datetime.now(datetime.UTC)
                        setting_is_dynamic = True
                        setting_is_protected = (name in protected_set)

                        settings_manager.set_setting(name, setting_value)
                        setting = db.query(Setting).filter_by(name=name).first()
                    else:
                        raise HTTPException(status_code=404, detail=f"Setting '{name}' not found (/api/settings/{name})")

        # Special handling for absolute paths
        # TODO: Simplify, the path logic is the same for all three settings below!
        if name == "absolute_image_directory":
            # Get base directory of FastAPI application (parent directory of settings_router.py)
            base_dir = pathlib.Path(__file__).parent.parent.absolute()

            # Combine base directory with the setting value
            full_path = os.path.join(str(base_dir), setting_value)

            # Normalize the path to remove any redundant separators
            normalized_path = os.path.normpath(full_path)
            setting_value = normalized_path

            logger.info(
                f"Got query for absolute_image_directory: Base directory={base_dir}, setting value={setting_value}, absolute path={normalized_path}"
            )
            setting_created_date = datetime.datetime.now(datetime.UTC)
        elif name == "absolute_upload_directory":
            # Get base directory of FastAPI application (parent directory of settings_router.py)
            base_dir = pathlib.Path(__file__).parent.parent.absolute()

            # Combine base directory with the setting value
            full_path = os.path.join(str(base_dir), setting_value)

            # Normalize the path to remove any redundant separators
            normalized_path = os.path.normpath(full_path)
            setting_value = normalized_path

            logger.info(
                f"Got query for absolute_upload_directory: Base directory={base_dir}, setting value={setting_value}, absolute path={normalized_path}"
            )
        elif name == "absolute_thumbnail_directory":
            # Get base directory of FastAPI application (parent directory of settings_router.py)
            base_dir = pathlib.Path(__file__).parent.parent.absolute()

            # Combine base directory with the setting value
            full_path = os.path.join(str(base_dir), setting_value)

            # Normalize the path to remove any redundant separators
            normalized_path = os.path.normpath(full_path)
            setting_value = normalized_path

            logger.info(
                f"Got query for absolute_thumbnail_directory: Base directory={base_dir}, setting value={setting_value}, absolute path={normalized_path}"
            )
        elif name == "thumbnail_settings":
            logger.info(f"Received query for thumbnail_settings")
            setting_value = {
                ''
            }
        else:
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
            settings_manager.initialize(db)

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
            settings_manager.initialize(db)
        protected_set = set(settings_manager.get_protected_settings())
        db_settings = db.query(Setting).all()
        return [s for s in db_settings if s.name.lower() not in protected_set]

    @router.get("/default_album_id")
    async def get_default_album(db: Session = Depends(db_dependency)):
        """
        Returns the default album ID.
        """
        if not settings_manager._initialized:
            settings_manager.initialize(db)

        album_id = settings_manager.get_setting("default_album_id", "")

        return {"name": "default_album_id", "value": album_id}

    @router.put("/default_album_id")
    async def update_default_album(setting_data: dict, db: Session = Depends(db_dependency)):
        """
        Updates the default album ID.
        """
        if not settings_manager._initialized:
            settings_manager.initialize(db)

        success = settings_manager.set_setting("default_album_id", setting_data.get("value", ""))

        if not success:
            raise HTTPException(status_code=500, detail="Fehler beim Aktualisieren der default_album_id-Einstellung")

        return {"name": "default_album_id", "value": setting_data.get("value", "")}

    @router.put("/thumbnail_settings")
    async def update_thumbnail_settings(
        thumbnail_directory: str,
        thumbnail_width: int,
        thumbnail_height: int,
        db: Session = Depends(db_dependency),
    ):
        """
        Updates the thumbnail settings (directory and size).
        """
        try:
            if not settings_manager._initialized:
                settings_manager.initialize(db)
            directory_success = settings_manager.set_setting("thumbnail_directory", thumbnail_directory)
            size_value = f"{thumbnail_width},{thumbnail_height}"
            size_success = settings_manager.set_setting("thumbnail_size", size_value)
            if not (directory_success and size_success):
                raise HTTPException(status_code=500, detail="Fehler beim Aktualisieren der Thumbnail-Einstellungen")
            return {"status": "success", "message": "Thumbnail settings saved successfully"}
        except Exception as e:
            logger.error(f"Error occurred while saving thumbnail settings: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error occurred while saving thumbnail settings: {str(e)}")

    @router.get("/thumbnail_settings", response_model=List[SettingResponse])
    async def get_thumbnail_settings(db: Session = Depends(db_dependency)) -> List[SettingResponse]:
        """
        Returns the current thumbnail settings (directory and size).
        """
        try:
            if not settings_manager._initialized:
                settings_manager.initialize(db)
            thumbnail_directory = settings_manager.get_setting("thumbnail_directory")
            thumbnail_size = settings_manager.get_setting("thumbnail_size")
            thumbnail_size_type = settings_manager.get_setting("thumbnail_size_type")

            # TODO: SettingsManager should not only provide value but SettingResponse for each setting?
            thumbnail_settings = [
                SettingResponse(
                    name="thumbnail_directory",
                    value=thumbnail_directory,
                    is_dynamic=True,
                    is_protected=False,
                    created_date=datetime.datetime.now(datetime.UTC),
                    updated_date=datetime.datetime.now(datetime.UTC)
                ),
                SettingResponse(
                    name="thumbnail_size",
                    value=thumbnail_size,
                    is_dynamic=True,
                    is_protected=False,
                    created_date=datetime.datetime.now(datetime.UTC),
                    updated_date=datetime.datetime.now(datetime.UTC)
                ),
                SettingResponse(
                    name="thumbnail_size_type",
                    value=thumbnail_size_type,
                    is_dynamic=True,
                    is_protected=False,
                    created_date=datetime.datetime.now(datetime.UTC),
                    updated_date=datetime.datetime.now(datetime.UTC)
                )
            ]

            json_response = JSONResponse(
                {
                    "thumbnail_directory": thumbnail_directory,
                    "thumbnail_size": thumbnail_size,
                    "thumbnail_size_type": thumbnail_size_type,
                })

            logger.info(f"Thumbnail settings: {thumbnail_settings}")

            return thumbnail_settings
        except Exception as e:
            logger.error(f"Error occurred while retrieving thumbnail settings: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error occurred while retrieving thumbnail settings: {str(e)}")

    @router.post("/reset_supported_formats", response_model=SettingResponse)
    async def reset_supported_formats(db: Session = Depends(db_dependency)):
        """
        Resets the supported image formats to the default value.
        """
        try:
            if not settings_manager._initialized:
                settings_manager.initialize(db)
            extensions = Image.registered_extensions()
            supported_extensions_str = ";".join(sorted(extensions.keys()))
            success = settings_manager.set_setting("supported_image_formats", supported_extensions_str)
            if not success:
                raise HTTPException(status_code=500, detail="Fehler beim Zurücksetzen der unterstützten Bildformate")
            setting = db.query(Setting).filter_by(name="supported_image_formats").first()
            return SettingResponse(
                id=setting.id,
                name="supported_image_formats",
                value=supported_extensions_str,
                created_date=setting.created_date,
                updated_date=setting.updated_date,
                is_protected=setting.is_protected,
                is_dynamic=setting.is_dynamic,
            )
        except Exception as e:
            logger.error(f"Error occurred while resetting supported image formats: {e}")
            raise HTTPException(status_code=500, detail=f"Error occurred while resetting supported image formats: {str(e)}")

    # Template rendering endpoints (only added if templates are enabled)
    if templates is not None:
        @router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
        async def settings_ui(request: Request, db: Session = Depends(db_dependency)):
            """
            Renders the settings UI using the configured template.
            This endpoint provides a web interface for viewing and editing settings.
            """
            if not settings_manager._initialized:
                settings_manager.initialize(db)

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
                settings_manager.initialize(db)

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
