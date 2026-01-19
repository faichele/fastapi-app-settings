from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, Column, DateTime, Integer, String

# Shared SQLAlchemy Base class
from fastapi_shared_orm import Base


# SQLAlchemy model for settings
class Setting(Base):
    __tablename__ = "rideto_settings"

    # Falls das Modul in seltenen Fällen doppelt importiert wird (z.B. durch dynamische Imports),
    # verhindert dies einen Crash. Besser ist: Importpfade konsolidieren.
    # TODO: Required?
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    value = Column(String, nullable=False)
    created_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_protected = Column(Boolean, default=False)
    is_dynamic = Column(Boolean, default=True)


class SettingBase(BaseModel):
    name: str
    value: str
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


# Definiert eine Liste aller erlaubten Einstellungsnamen
ALLOWED_SETTINGS = [
    # Paths and directories
    "image_directory",
    "absolute_image_directory",
    "thumbnail_directory",
    "absolute_thumbnail_directory",
    "upload_directory",
    "absolute_upload_directory",

    # Thumbnails
    "thumbnail_size",
    "thumbnail_size_type",

    # Supported image formats (and aliases)
    # TODO: Clean up aliases - this is a mess
    "supported_image_formats",
    "supported_formats",
    "formats",

    # Alben
    "default_album_id",

    # Anwendungseinstellungen
    "environment",
    "frontend_host",
    "api_prefix",

    # CORS Einstellungen
    "backend_cors_origins",

    # E-Mail Einstellungen (nicht-sensitive Teile)
    "email_reset_token_expire_hours",
    "emails_from_name",

    # Sonstige Einstellungen
    "project_name",
]

# Liste der schützenswerten Einstellungen, die nicht in der Datenbank gespeichert werden sollen
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
