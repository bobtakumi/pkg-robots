import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(path: Path | None = None) -> dict:
    p = path or ROOT / "config.toml"
    with open(p, "rb") as f:
        cfg = tomllib.load(f)
    cfg["_root"] = ROOT
    return cfg
