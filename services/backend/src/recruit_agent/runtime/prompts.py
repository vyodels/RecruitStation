from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .models import Message


@dataclass(slots=True)
class PromptLoader:
    root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / "prompts")

    def load_text(self, relative_path: str) -> str:
        path = self.root / relative_path
        if not path.exists():
            raise FileNotFoundError(path)
        return path.read_text(encoding="utf-8")

    def has_prompt(self, relative_path: str) -> bool:
        return (self.root / relative_path).exists()


class _SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


@dataclass(slots=True)
class PromptBuilder:
    loader: PromptLoader = field(default_factory=PromptLoader)
    base_prompts: tuple[str, ...] = ("base/identity.md", "base/behavior_rules.md", "base/output_format.md")

    def render(self, template: str, values: Mapping[str, Any] | None = None) -> str:
        data = _SafeDict()
        if values:
            data.update(values)
        return template.format_map(data)

    def build_system_prompt(self, task_type: str, context: Mapping[str, Any] | None = None) -> str:
        parts = [self.loader.load_text(path).strip() for path in self.base_prompts]
        task_path = f"tasks/{task_type}.md"
        if self.loader.has_prompt(task_path):
            parts.append(self.render(self.loader.load_text(task_path), context or {}).strip())
        return "\n\n---\n\n".join(part for part in parts if part)

    def build_user_prompt(
        self,
        task_type: str,
        context: Mapping[str, Any] | None = None,
        extra_sections: Mapping[str, Any] | None = None,
    ) -> str:
        sections: list[str] = []
        if context:
            for key, value in context.items():
                sections.append(f"## {key}\n\n{value}")
        if extra_sections:
            for key, value in extra_sections.items():
                sections.append(f"## {key}\n\n{value}")
        return "\n\n---\n\n".join(section for section in sections if section)

    def build_messages(
        self,
        task: Any,
        *,
        session: Mapping[str, Any] | None = None,
        skill: Mapping[str, Any] | None = None,
        extra_context: Mapping[str, Any] | None = None,
    ) -> list[Message]:
        task_type = getattr(task, "task_type", None) or getattr(task, "workflow_node_id", None) or "initial_screening"
        payload_context = dict(getattr(task, "payload", {}) or {})
        if extra_context:
            payload_context.update(extra_context)
        if session:
            payload_context.setdefault("session", session)
        if skill:
            payload_context.setdefault("skill", skill)

        system_prompt = self.build_system_prompt(task_type, payload_context)
        user_prompt = self.build_user_prompt(
            task_type,
            context=payload_context,
            extra_sections={
                "task": getattr(task, "payload", {}) or {},
            },
        )
        if skill:
            user_prompt = "\n\n---\n\n".join(
                part for part in [user_prompt, f"## Skill Reference\n\n{skill}"] if part
            )

        messages = [Message(role="system", content=system_prompt)]
        if user_prompt:
            messages.append(Message(role="user", content=user_prompt))
        return messages
