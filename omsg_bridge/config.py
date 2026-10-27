import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG = Path.home() / ".config/omsg-bridge/settings.toml"


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8787
    imsg: str = "imsg"
    command_timeout: float = 60
    auth_enabled: bool = True
    username: str = ""
    password: str = ""

    def validate(self):
        if not isinstance(self.host, str) or not self.host:
            raise ValueError("host must be a nonempty hostname or address")
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if not isinstance(self.imsg, str) or not self.imsg:
            raise ValueError("imsg must be an executable name or path")
        if type(self.command_timeout) not in (int, float) or not 0 < self.command_timeout <= 3600:
            raise ValueError("command_timeout must be between 0 and 3600 seconds")
        if type(self.auth_enabled) is not bool:
            raise ValueError("auth.enabled must be true or false")
        if not isinstance(self.username, str) or not isinstance(self.password, str):
            raise ValueError("auth username and password must be strings")
        if self.auth_enabled and (not self.username or not self.password or ":" in self.username):
            raise ValueError(
                "Set auth username and password (username cannot contain ':') in settings.toml"
            )
        return self


def load_settings(path=DEFAULT_CONFIG, environ=None):
    environ = os.environ if environ is None else environ
    data = tomllib.loads(Path(path).read_text()) if Path(path).exists() else {}
    if set(data) - {"host", "port", "imsg", "command_timeout", "auth"}:
        raise ValueError("Unknown settings key")
    auth = data.pop("auth", {})
    if not isinstance(auth, dict) or set(auth) - {"enabled", "username", "password"}:
        raise ValueError("Invalid auth settings")
    if "PORT" in environ:
        try:
            data["port"] = int(environ["PORT"])
        except ValueError as exc:
            raise ValueError("PORT must be a numeric port") from exc
    return Settings(
        **data,
        auth_enabled=auth.get("enabled", True),
        username=auth.get("username", ""),
        password=auth.get("password", ""),
    ).validate()
