from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[3]


def test_legacy_runtime_paths_are_removed() -> None:
    missing_targets = [
        BACKEND_ROOT / "src" / "recruit_station" / "runtime" / "agent_loop.py",
        BACKEND_ROOT / "src" / "recruit_station" / "runtime" / "prompts.py",
        BACKEND_ROOT / "src" / "recruit_station" / "services" / "agent.py",
        BACKEND_ROOT / "src" / "recruit_station" / "services" / "autonomy.py",
        BACKEND_ROOT / "src" / "recruit_station" / "services" / "runtime.py",
        BACKEND_ROOT / "src" / "recruit_station" / "services" / "runtime_control.py",
        BACKEND_ROOT / "src" / "recruit_station" / "services" / "context_assembler.py",
        BACKEND_ROOT / "src" / "recruit_station" / "api" / "routers" / "runtime.py",
        BACKEND_ROOT / "tests" / "test_runtime_agent_loop.py",
        BACKEND_ROOT / "tests" / "test_runtime_prompts.py",
        BACKEND_ROOT / "tests" / "test_runtime_tools.py",
        BACKEND_ROOT / "tests" / "test_api_runtime.py",
        BACKEND_ROOT / "tests" / "test_autonomy_loop.py",
    ]

    present = [str(path.relative_to(BACKEND_ROOT)) for path in missing_targets if path.exists()]
    assert not present, f"legacy cutover paths still present: {present}"


def test_legacy_backend_package_name_is_removed() -> None:
    src_root = BACKEND_ROOT / "src"
    legacy_package_names = {path.name for path in src_root.iterdir() if path.is_dir()}
    assert not any(name.endswith("_pilot") for name in legacy_package_names)
