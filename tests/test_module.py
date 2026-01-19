import os
import tempfile
import importlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def setup_sqlite_file_db(tmp_name: str = "app_settings_test.db"):
    tmp_dir = tempfile.gettempdir()
    db_path = os.path.join(tmp_dir, tmp_name)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    from backend.database import base as db_base  # type: ignore
    importlib.reload(db_base)
    db_base.Base.metadata.create_all(bind=db_base.engine)
    return db_base


def test_defaults_and_merge(tmp_path: Path):
    db_base = setup_sqlite_file_db("app_settings_defaults.db")

    extra = tmp_path / "extra_settings.py"
    extra.write_text(
        "\n".join([
            "ALLOWED_SETTINGS = ['custom_allowed', 'new_default']",
            "PROTECTED_SETTINGS = ['custom_protected']",
            "DEFAULT_SETTINGS_VALUES = {'new_default': 'foo'}",
        ])
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

    # GET on new_default should seed with default value
    r = client.get("/api/settings/new_default")
    assert r.status_code == 200
    assert r.json()["value"] == "foo"

    # PUT on custom_allowed is accepted
    r = client.put("/api/settings/custom_allowed", json={"value": "42"})
    assert r.status_code == 200

    # Protected is blocked
    r = client.put("/api/settings/custom_protected", json={"value": "x"})
    assert r.status_code == 403


def test_dynamic_router(tmp_path: Path):
    db_base = setup_sqlite_file_db("app_settings_dynamic_router2.db")

    extra_router_file = tmp_path / "my_extra_router.py"
    extra_router_file.write_text(
        "\n".join([
            "from fastapi import APIRouter",
            "router = APIRouter()",
            "@router.get('/ping')",
            "def ping():",
            "    return {'pong': True}",
        ])
    )

    from fastapi_app_settings import create_settings_router
    app = FastAPI()
    app.include_router(
        create_settings_router(
            prefix="/api/settings",
            get_db=db_base.get_db,
            app_root=tmp_path,
            extra_router_file="my_extra_router.py",
        )
    )
    client = TestClient(app)
    r = client.get("/api/settings/ping")
    assert r.status_code == 200
    assert r.json() == {"pong": True}

