from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

SHARED_WORKSPACE_SCOPE_REF = "workspace:shared"

_META_SECTION = "__meta__"
_SUMMARY_SECTION = "summary"
_GOAL_TEXT_SECTION = "goal text"
_CONSTRAINTS_SECTION = "constraints"
_SUCCESS_CRITERIA_SECTION = "success criteria"
_CONTEXT_HINTS_SECTION = "context hints"


def shared_scene_template_catalog() -> dict[str, dict[str, Any]]:
    return dict(_load_shared_scene_template_catalog())


def serialize_scene_template(template: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": template["key"],
        "title": template["title"],
        "summary": template["summary"],
        "goal_kind": template["goal_kind"],
        "goalKind": template["goal_kind"],
        "default_goal_text": template["default_goal_text"],
        "defaultGoalText": template["default_goal_text"],
        "requires_jd": bool(template.get("requires_jd")),
        "requiresJd": bool(template.get("requires_jd")),
        "supports_candidate_count_target": bool(template.get("supports_candidate_count_target")),
        "supportsCandidateCountTarget": bool(template.get("supports_candidate_count_target")),
        "default_candidate_count_target": template.get("default_candidate_count_target"),
        "defaultCandidateCountTarget": template.get("default_candidate_count_target"),
        "direct_runnable": bool(template.get("direct_runnable")),
        "directRunnable": bool(template.get("direct_runnable")),
        "constraints": dict(template.get("constraints") or {}),
        "success_criteria": dict(template.get("success_criteria") or {}),
        "successCriteria": dict(template.get("success_criteria") or {}),
        "context_hints": dict(template.get("context_hints") or {}),
        "contextHints": dict(template.get("context_hints") or {}),
    }


@lru_cache(maxsize=1)
def _load_shared_scene_template_catalog() -> dict[str, dict[str, Any]]:
    ordered_templates: list[dict[str, Any]] = []
    for path in sorted(_scene_templates_root().glob("*.md")):
        template = _parse_scene_template_doc(path)
        ordered_templates.append(template)
    ordered_templates.sort(key=lambda item: (int(item.get("display_order", 1000)), str(item.get("key") or "")))

    catalog: dict[str, dict[str, Any]] = {}
    for template in ordered_templates:
        catalog[template["key"]] = template
    return catalog


def _parse_scene_template_doc(path: Path) -> dict[str, Any]:
    title, sections = _parse_markdown_sections(path)
    metadata = _parse_mapping_block(path=path, block_name="Meta", lines=sections.get(_META_SECTION, []))
    constraints = _parse_mapping_block(path=path, block_name="Constraints", lines=sections.get(_CONSTRAINTS_SECTION, []))
    success_criteria = _parse_mapping_block(
        path=path,
        block_name="Success Criteria",
        lines=sections.get(_SUCCESS_CRITERIA_SECTION, []),
    )
    context_hints = _parse_mapping_block(path=path, block_name="Context Hints", lines=sections.get(_CONTEXT_HINTS_SECTION, []))

    key = str(metadata.get("key") or path.stem).strip()
    goal_kind = str(metadata.get("goal_kind") or key).strip()
    template: dict[str, Any] = {
        "key": key,
        "title": title,
        "summary": _parse_text_block(path=path, block_name="Summary", lines=sections.get(_SUMMARY_SECTION, [])),
        "goal_kind": goal_kind,
        "default_goal_text": _parse_text_block(path=path, block_name="Goal Text", lines=sections.get(_GOAL_TEXT_SECTION, [])),
        "requires_jd": bool(metadata.get("requires_jd", False)),
        "supports_candidate_count_target": bool(metadata.get("supports_candidate_count_target", False)),
        "direct_runnable": bool(metadata.get("direct_runnable", False)),
        "constraints": constraints,
        "success_criteria": success_criteria,
        "context_hints": context_hints,
    }
    if "default_candidate_count_target" in metadata:
        template["default_candidate_count_target"] = metadata["default_candidate_count_target"]
    if "display_order" in metadata:
        template["display_order"] = metadata["display_order"]
    return template


def _parse_markdown_sections(path: Path) -> tuple[str, dict[str, list[str]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = ""
    sections: dict[str, list[str]] = {_META_SECTION: []}
    current_section = _META_SECTION
    for line in lines:
        stripped = line.strip()
        if not stripped and current_section == _META_SECTION and not sections[_META_SECTION]:
            continue
        if stripped.startswith("# "):
            if not title:
                title = stripped[2:].strip()
                continue
        if stripped.startswith("## "):
            current_section = stripped[3:].strip().lower()
            sections.setdefault(current_section, [])
            continue
        sections.setdefault(current_section, []).append(line)
    if not title:
        raise ValueError(f"Scene template doc missing title heading: {path}")
    return title, sections


def _parse_mapping_block(*, path: Path, block_name: str, lines: list[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        if not stripped.startswith("- ") or ":" not in stripped[2:]:
            raise ValueError(f"Scene template doc has invalid {block_name} entry: {path}: {raw_line}")
        key, raw_value = stripped[2:].split(":", 1)
        payload[key.strip()] = _coerce_scalar(raw_value.strip())
    return payload


def _parse_text_block(*, path: Path, block_name: str, lines: list[str]) -> str:
    text = "\n".join(line.rstrip() for line in lines).strip()
    if not text:
        raise ValueError(f"Scene template doc missing {block_name}: {path}")
    return text


def _coerce_scalar(value: str) -> Any:
    normalized = value.strip()
    lowered = normalized.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    if lowered.lstrip("-").isdigit():
        return int(lowered)
    return normalized


def _scene_templates_root() -> Path:
    return Path(__file__).resolve().parent.parent / "prompts" / "scene_templates"
