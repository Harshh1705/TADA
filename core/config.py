from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path.home() / ".FolioPy"
CONFIG_FILE = CONFIG_DIR / "config.env"


class Config(BaseSettings):
    supabase_url: str = ""
    supabase_key: str = ""
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model: Optional[str] = None
    tavily_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=[".env", str(CONFIG_FILE)],
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_config() -> Config:
    return Config()


def write_config(**kwargs) -> Config:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    existing = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    existing[k.upper()] = v
    existing.update({k.upper(): v for k, v in kwargs.items() if v is not None})
    with open(CONFIG_FILE, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    return load_config()


def show_config() -> dict:
    cfg = load_config()
    d = cfg.model_dump()
    for key in ("supabase_key", "llm_api_key", "tavily_api_key"):
        val = d.get(key, "")
        if val and len(val) > 4:
            d[key] = val[:3] + "..." + val[-4:]
        elif val:
            d[key] = "***"
    return d
