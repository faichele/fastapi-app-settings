import importlib
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def setup_sqlite_file_db(db_path: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    from backend.database import base as db_base  # type: ignore
    importlib.reload(db_base)
    db_base.Base.metadata.create_all(bind=db_base.engine)
    return db_base


def test_extra_settings_map_is_used_for_defaults(tmp_path: Path):
    db_base = setup_sqlite_file_db(tmp_path / "app_settings_extra_map_defaults.db")

    extra = tmp_path / "extra_settings.py"
    extra.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "ALLOWED_SETTINGS = ['dyn_setting']",
                "DEFAULT_SETTINGS_VALUES = {}",
                "def _resolver(ctx):",
                "    # ctx is a SettingsManagerContext",
                "    return str(Path(ctx.app_root_path) / 'dynamic')",
                "EXTRA_SETTINGS_MAP = {'dyn_setting': _resolver}",
            ]
        )
    )

    from fastapi_app_settings import create_settings_router

    app = FastAPI()
    app.include_router(
        create_settings_router(
            prefix="/api/settings",
            get_db=db_base.get_db,
            app_root=tmp_path,
            extra_settings_file="extra_settings.py",
        )
    )

    client = TestClient(app)
    r = client.get("/api/settings/dyn_setting")
    assert r.status_code == 200
    assert r.json()["value"].endswith("/dynamic")

