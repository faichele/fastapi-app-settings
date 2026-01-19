from .settings_manager import SettingsManager, settings_manager
from .router import create_settings_router
from .models import (
    Setting,
    SettingBase,
    SettingCreate,
    SettingUpdate,
    SettingResponse,
    ALLOWED_SETTINGS,
    PROTECTED_SETTINGS,
)

__version__ = "0.0.2"

__all__ = [
    "SettingsManager",
    "settings_manager",
    "create_settings_router",
    "Setting",
    "SettingBase",
    "SettingCreate",
    "SettingUpdate",
    "SettingResponse",
    "ALLOWED_SETTINGS",
    "PROTECTED_SETTINGS",
]
