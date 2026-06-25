from datetime import datetime, timezone
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict

from model_factory import configure_setting_models  # noqa: F401 – re-exported for convenience

# SQLAlchemy-ORM-Modell wird NICHT statisch hier erzeugt.
# Es wird dynamisch durch configure_setting_models() in dieses Modul eingebunden.
# Nach dem Aufruf von configure_setting_models() ist folgendes Attribut verfügbar:
#   - fastapi_app_settings.Setting
# In Anwendungen wird empfohlen, das Setting-Modell über das database-Package zu
# importieren (z. B. `from database import Setting`), da dort der Aufruf von
# configure_setting_models() mit dem korrekten Präfix garantiert ist.
Setting: type = None  # type: ignore[assignment]  – wird durch configure_setting_models() ersetzt


class SettingBase(BaseModel):
    name: str
    value: Any
    min_value: Optional[str] = None
    max_value: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SettingCreate(SettingBase):
    pass


class SettingUpdate(BaseModel):
    value: str
    is_protected: Optional[bool] = None
    is_dynamic: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class SettingResponse(SettingBase):
    id: Optional[int] = None
    is_protected: bool
    is_dynamic: bool
    created_date: datetime
    updated_date: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# List of public settings
ALLOWED_SETTINGS = [
    # Application settings
    "environment",
    "frontend_host",
    "api_prefix",

    # CORS settings
    "backend_cors_origins",

    # E-mail settings (non-sensitive parts)
    "email_reset_token_expire_hours",
    "emails_from_name",

    # Project name
    "project_name",
]

# List of all read-only settings
# TODO: Make this configurable, and non-agnostic to a specific project
READONLY_SETTINGS = [
    # Supported image formats (and aliases)
    # TODO: Clean up aliases - this is a mess
    "supported_image_formats",
    "supported_formats",
    "formats",
]

# List of all protected settings
# Not saved in database
# TODO: Make this configurable, and non-agnostic to a specific project
# Protected settings not stored in the database
# Read from environment variables or .env file, not editable via API
PROTECTED_SETTINGS = [
    "secret_key",
    "postgres_server",
    "postgres_user",
    "postgres_password",
    "postgres_db",
    "smtp_host",
    "smtp_user",
    "smtp_password",
    "emails_from_email",
    "first_superuser",
    "first_superuser_password",
    "sentry_dsn",
]
