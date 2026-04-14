from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .models import ToolExecutionResult


class ToolExecutionError(RuntimeError):
    pass


class ToolHandler(Protocol):
    def __call__(self, arguments: dict[str, Any]) -> Any: ...


@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_provider_spec(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass(slots=True)
class ToolRegistry:
    tools: dict[str, ToolDefinition] = field(default_factory=dict)

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self.tools:
            raise ToolExecutionError(f"Tool already registered: {tool.name}")
        self.tools[tool.name] = tool

    def has(self, tool_name: str) -> bool:
        return tool_name in self.tools

    def describe(self) -> list[dict[str, Any]]:
        return [tool.to_provider_spec() for tool in self.tools.values()]

    def execute(self, tool_name: str, arguments: dict[str, Any] | None = None) -> ToolExecutionResult:
        if tool_name not in self.tools:
            raise ToolExecutionError(f"Unknown tool: {tool_name}")
        tool = self.tools[tool_name]
        try:
            output = tool.handler(arguments or {})
            return ToolExecutionResult(tool_name=tool_name, output=output, is_error=False)
        except Exception as exc:  # pragma: no cover - defensive guard
            return ToolExecutionResult(tool_name=tool_name, output=str(exc), is_error=True)

    def build_result_submission_tool(self, name: str = "submit_result") -> ToolDefinition:
        def _handler(arguments: dict[str, Any]) -> dict[str, Any]:
            return {"accepted": True, "payload": arguments}

        return ToolDefinition(
            name=name,
            description="Submit a structured task result.",
            parameters={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "data": {"type": "object"},
                },
                "required": ["status"],
                "additionalProperties": True,
            },
            handler=_handler,
            metadata={"terminal_result_submission": True},
        )

    def build_system_command_tool(
        self,
        handler: ToolHandler,
        *,
        name: str = "request_system_command",
    ) -> ToolDefinition:
        return ToolDefinition(
            name=name,
            description="Request a whitelisted system command via desktop approval. Execution is disabled by default.",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                    "rationale": {"type": "string"},
                    "requested_by": {"type": "string"},
                    "metadata": {"type": "object"},
                },
                "required": ["command"],
                "additionalProperties": False,
            },
            handler=handler,
            metadata={
                "requires_approval": True,
                "feature_flag": "skills.system_command",
                "execution_enabled": False,
            },
        )
