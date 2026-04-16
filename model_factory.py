"""Factory und Konfiguration für ORM-Modelle des Settings-Moduls.

Das Paket kann sein SQLAlchemy-ORM-Modell gegen eine injizierte Declarative-Base
mit optionalem Tabellenpräfix erzeugen. Standardmäßig bleibt das bisherige
Tabellenschema mit ``rideto_settings`` erhalten.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import sys
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Integer, String

DEFAULT_SETTING_TABLE_PREFIX = "rideto_"


@dataclass(frozen=True)
class SettingORMModels:
    """Bundle des erzeugten ORM-Modells und seines Tabellennamens."""

    Setting: type[Any]
    table_prefix: str
    setting_table_name: str


def _normalize_prefix(table_prefix: str | None) -> str:
    return table_prefix or ""


def _class_name_suffix(table_prefix: str) -> str:
    suffix = re.sub(r"\W+", "_", table_prefix).strip("_")
    return suffix or "default"


def _cache_for_base(base: type[Any]) -> dict[str, SettingORMModels]:
    metadata = getattr(base, "metadata")
    return metadata.info.setdefault("_fastapi_app_settings_model_cache", {})


def _patch_module(module_name: str, **updates: Any) -> None:
    module = sys.modules.get(module_name)
    if module is None:
        return
    for attribute_name, value in updates.items():
        setattr(module, attribute_name, value)


def create_setting_models(
    base: type[Any],
    table_prefix: str = DEFAULT_SETTING_TABLE_PREFIX,
) -> SettingORMModels:
    """Erzeugt das Setting-ORM-Modell für eine gegebene Base.

    Args:
        base: Declarative Base bzw. abgeleitete Basisklasse der Anwendung.
        table_prefix: Optionales Präfix für die Settings-Tabelle.
            Standardmäßig ``rideto_`` zur Wahrung der bisherigen Tabellennamen.

    Returns:
        Ein Bundle mit dem erzeugten ORM-Modell.
    """

    normalized_prefix = _normalize_prefix(table_prefix)
    base_cache = _cache_for_base(base)
    cached_models = base_cache.get(normalized_prefix)
    if cached_models is not None:
        return cached_models

    class_suffix = _class_name_suffix(normalized_prefix)
    setting_table_name = f"{normalized_prefix}settings"

    setting_attrs = {
        "__module__": __name__,
        "__tablename__": setting_table_name,
        "id": Column(Integer, primary_key=True, index=True),
        "name": Column(String, unique=True, nullable=False, index=True),
        "value": Column(String, nullable=False),
        "created_date": Column(DateTime, default=lambda: datetime.now(timezone.utc)),
        "updated_date": Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        "is_protected": Column(Boolean, default=False),
        "is_dynamic": Column(Boolean, default=True),
    }
    Setting = type(f"SettingModel_{class_suffix}", (base,), setting_attrs)

    bundle = SettingORMModels(
        Setting=Setting,
        table_prefix=normalized_prefix,
        setting_table_name=setting_table_name,
    )
    base_cache[normalized_prefix] = bundle
    return bundle


def configure_setting_models(
    base: type[Any],
    table_prefix: str = DEFAULT_SETTING_TABLE_PREFIX,
) -> SettingORMModels:
    """Konfiguriert die öffentlichen ORM-Aliasse des Pakets für Base + Präfix."""

    bundle = create_setting_models(base, table_prefix=table_prefix)
    module_updates = {"Setting": bundle.Setting}

    for module_name in (
        "fastapi_app_settings.models",
        "fastapi_app_settings.settings_manager",
        "fastapi_app_settings.router",
        "fastapi_app_settings",
        "packages.fastapi_app_settings.models",
        "packages.fastapi_app_settings.settings_manager",
        "packages.fastapi_app_settings.router",
        "packages.fastapi_app_settings",
    ):
        _patch_module(module_name, **module_updates)

    return bundle


__all__ = [
    "DEFAULT_SETTING_TABLE_PREFIX",
    "SettingORMModels",
    "create_setting_models",
    "configure_setting_models",
]

