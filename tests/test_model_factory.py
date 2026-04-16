from pathlib import Path

import importlib
import sys
from sqlalchemy.orm import declarative_base

repo_root = Path(__file__).resolve().parents[3]
packages_root = repo_root / "packages"
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(packages_root))

from fastapi_shared_orm import Base as SharedBase
from fastapi_app_settings import (
    DEFAULT_SETTING_TABLE_PREFIX,
    configure_setting_models,
    create_setting_models,
)

models_module = importlib.import_module("fastapi_app_settings.models")
router_module = importlib.import_module("fastapi_app_settings.router")
settings_manager_module = importlib.import_module("fastapi_app_settings.settings_manager")


def test_create_setting_models_preserves_default_table_and_caches_per_base_prefix():
    TestBase = declarative_base()

    default_models = create_setting_models(TestBase)
    same_default_models = create_setting_models(TestBase)
    prefixed_models = create_setting_models(TestBase, table_prefix="tenant_")
    plain_models = create_setting_models(TestBase, table_prefix="")

    assert default_models is same_default_models
    assert default_models.Setting is same_default_models.Setting
    assert default_models.table_prefix == DEFAULT_SETTING_TABLE_PREFIX
    assert default_models.setting_table_name == "rideto_settings"
    assert default_models.Setting.__tablename__ == "rideto_settings"

    assert prefixed_models.Setting is not default_models.Setting
    assert prefixed_models.setting_table_name == "tenant_settings"
    assert prefixed_models.Setting.__tablename__ == "tenant_settings"

    assert plain_models.setting_table_name == "settings"
    assert plain_models.Setting.__tablename__ == "settings"


def test_configure_setting_models_rebinds_public_aliases():
    TestBase = declarative_base()
    default_models = create_setting_models(SharedBase)

    try:
        configured_models = configure_setting_models(TestBase, table_prefix="demo_")

        assert models_module.Setting is configured_models.Setting
        assert settings_manager_module.Setting is configured_models.Setting
        assert router_module.Setting is configured_models.Setting
        assert configured_models.Setting.__tablename__ == "demo_settings"
    finally:
        configure_setting_models(SharedBase, table_prefix=default_models.table_prefix)
