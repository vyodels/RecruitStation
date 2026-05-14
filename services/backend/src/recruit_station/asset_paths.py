from __future__ import annotations

from pathlib import Path


def recruit_station_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".recruit-station"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("missing .recruit-station asset root")


def prompts_root() -> Path:
    return recruit_station_root() / "prompts"


def prompt_path(prompt_key: str) -> Path:
    normalized = str(prompt_key).strip().strip("/")
    return prompts_root() / f"{normalized}.md"


def scene_templates_root() -> Path:
    return prompts_root() / "scene_templates"


def plugin_asset_path(*parts: str) -> Path:
    return recruit_station_root() / "plugins" / Path(*parts)


def skills_root() -> Path:
    return recruit_station_root() / "skills"


def mcp_root() -> Path:
    return recruit_station_root() / "mcp"


def mcp_preset_templates_root() -> Path:
    return mcp_root() / "presets"


def communication_templates_root() -> Path:
    return recruit_station_root() / "communication_templates"
