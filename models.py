from datetime import datetime, timezone
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict

# Shared SQLAlchemy Base class
from fastapi_shared_orm import Base

from .model_factory import create_setting_models

_DEFAULT_SETTING_MODELS = create_setting_models(Base)
Setting = _DEFAULT_SETTING_MODELS.Setting


class SettingBase(BaseModel):
    name: str
    value: Any
    is_protected: bool = False
    is_dynamic: bool = True


class SettingCreate(SettingBase):
    pass


class SettingUpdate(BaseModel):
    value: str
    is_protected: Optional[bool] = None
    is_dynamic: Optional[bool] = None


class SettingResponse(SettingBase):
    id: int
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
