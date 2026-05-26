from __future__ import annotations

from recruit_station.agents.autonomous import _runtime_tool_registry_for_run
from recruit_station.capabilities.tools import ToolDefinition, ToolRegistry
from recruit_station.models import AgentRun


def _tool(name: str) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=name,
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        handler=lambda arguments: {"ok": True},
    )


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(_tool("list_mcp_resources"))
    registry.register(_tool("read_mcp_resource"))
    registry.register(_tool("browser_get_active_tab"))
    registry.register(_tool("list_job_descriptions"))
    return registry


def test_jd_sync_runtime_hides_mcp_resource_tools_from_model_tool_surface() -> None:
    scoped = _runtime_tool_registry_for_run(
        _registry(),
        run=AgentRun(run_type="jd_sync"),
        constraints={},
    )

    assert "list_mcp_resources" not in scoped.tools
    assert "read_mcp_resource" not in scoped.tools
    assert "browser_get_active_tab" in scoped.tools
    assert "list_job_descriptions" in scoped.tools


def test_browser_target_runtime_hides_resource_tools_but_keeps_browser_tools() -> None:
    scoped = _runtime_tool_registry_for_run(
        _registry(),
        run=AgentRun(run_type="automation_recruiting"),
        constraints={"browser_target": {"url": "http://127.0.0.1:4317/jobs"}},
    )

    assert "list_mcp_resources" not in scoped.tools
    assert "read_mcp_resource" not in scoped.tools
    assert "browser_get_active_tab" in scoped.tools


def test_non_browser_runtime_keeps_resource_tools() -> None:
    scoped = _runtime_tool_registry_for_run(
        _registry(),
        run=AgentRun(run_type="analysis"),
        constraints={},
    )

    assert "list_mcp_resources" in scoped.tools
    assert "read_mcp_resource" in scoped.tools
