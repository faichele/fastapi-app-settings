from .settings_manager import SettingsManager, settings_manager
from .router import create_settings_router
from .model_factory import (
    DEFAULT_SETTING_TABLE_PREFIX,
    SettingORMModels,
    create_setting_models,
    configure_setting_models,
)
from .models import (
    Setting,
    SettingBase,
    SettingCreate,
    SettingUpdate,
    SettingResponse,
    ALLOWED_SETTINGS,
    PROTECTED_SETTINGS,
    READONLY_SETTINGS
)

__version__ = "0.0.3"

__all__ = [
    "SettingsManager",
    "settings_manager",
    "create_settings_router",
    "DEFAULT_SETTING_TABLE_PREFIX",
    "SettingORMModels",
    "create_setting_models",
    "configure_setting_models",
    "Setting",
    "SettingBase",
    "SettingCreate",
    "SettingUpdate",
    "SettingResponse",
    "ALLOWED_SETTINGS",
    "PROTECTED_SETTINGS",
    "READONLY_SETTINGS"
]
