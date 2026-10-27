import base64

import pytest

from omsg_bridge.config import Settings, load_settings
from omsg_bridge.server import create_app


def auth(username="tester", password="fixture-only"):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_auth_required_by_default(tmp_path):
    with pytest.raises(ValueError, match="username and password"):
        load_settings(tmp_path / "missing.toml", {})


def test_config_and_port_override(tmp_path):
    path = tmp_path / "settings.toml"
    path.write_text('host = "localhost"\nport = 8888\n[auth]\nenabled = false\n')
    settings = load_settings(path, {"PORT": "9000"})
    assert (settings.host, settings.port, settings.auth_enabled) == ("localhost", 9000, False)
    for value in ("0", "65536", "nope"):
        with pytest.raises(ValueError, match="port"):
            load_settings(path, {"PORT": value})


@pytest.mark.parametrize(
    "auth_line", ['enabled = "false"', 'username = "bad:name"\npassword = "x"']
)
def test_invalid_config(tmp_path, auth_line):
    path = tmp_path / "settings.toml"
    path.write_text(f"[auth]\n{auth_line}\n")
    with pytest.raises(ValueError):
        load_settings(path, {})


async def test_http_auth_and_health(aiohttp_client):
    client = await aiohttp_client(create_app(Settings(username="tester", password="fixture-only")))
    for path in ("/health", "/docs/openapi.json", "/docs/ui"):
        response = await client.get(path)
        assert response.status == 401
        assert response.headers["WWW-Authenticate"].startswith("Basic")
        response = await client.get(path, headers=auth(password="wrong"))
        assert response.status == 401
        response = await client.get(path, headers=auth())
        assert response.status == 200
    health = await (await client.get("/health", headers=auth())).json()
    assert health["status"] == "ok"
    assert "imsg_available" in health


async def test_cross_origin_rejected(aiohttp_client):
    client = await aiohttp_client(create_app(Settings(auth_enabled=False)))
    response = await client.get("/health", headers={"Origin": "https://attacker.invalid"})
    assert response.status == 403


async def test_docs_are_local_and_openapi_valid(aiohttp_client):
    from openapi_spec_validator import validate

    client = await aiohttp_client(create_app(Settings(auth_enabled=False)))
    spec = await (await client.get("/docs/openapi.json")).json()
    validate(spec)
    assert "/health" in spec["paths"]
    html = await (await client.get("/docs/ui")).text()
    assert "https://" not in html
    assert (await client.get("/docs/assets/swagger-ui-bundle.js")).status == 200
