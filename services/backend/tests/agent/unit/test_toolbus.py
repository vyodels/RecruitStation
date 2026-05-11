from __future__ import annotations

import asyncio
from pathlib import Path

from recruit_agent.runtime.tools import ToolDefinition, ToolRegistry, build_delegate_scene_context_tool, is_scene_context_tool, register_core_tools
from recruit_agent.runtime.models import CancellationToken
from recruit_agent.core.settings import AppSettings
from recruit_agent.db.session import create_engine_from_settings, create_session_factory, initialize_database
from recruit_agent.memory.service import MemoryService
from recruit_agent.models.domain import Candidate, RecruitAgentProfile
from recruit_agent.services.container import _build_read_memory_handler, _build_record_learning_handler


async def _run_async(tool_registry: ToolRegistry, tool_name: str, arguments: dict[str, object], token: CancellationToken | None = None):
    return await tool_registry.execute_async(tool_name, arguments, cancel_token=token)


def test_toolbus_executes_async_and_sync_tools_and_merges_sources() -> None:
    registry = ToolRegistry()

    async def _async_handler(arguments: dict[str, object], *, cancel_token: CancellationToken | None = None) -> dict[str, object]:
        assert cancel_token is not None
        return {"echo": arguments, "cancelled": cancel_token.cancelled}

    registry.register(
        ToolDefinition(
            name="core.echo",
            description="Echo content.",
            parameters={"type": "object"},
            handler=_async_handler,
            category="core",
            external_target=False,
            resource_target_kind="memory",
        )
    )
    register_core_tools(registry)

    plugin_registry = ToolRegistry()
    plugin_registry.register(
        ToolDefinition(
            name="plugin.note",
            description="Record note.",
            parameters={"type": "object"},
            handler=lambda arguments: {"noted": arguments.get("note")},
            category="plugin",
            external_target=False,
            resource_target_kind="candidate",
        )
    )
    registry.merge(plugin_registry)

    token = CancellationToken()
    result = asyncio.run(_run_async(registry, "core.echo", {"value": 1}, token))
    plugin_result = asyncio.run(_run_async(registry, "plugin.note", {"note": "hello"}))

    assert result.is_error is False
    assert result.output == {"echo": {"value": 1}, "cancelled": False}
    assert plugin_result.output == {"noted": "hello"}
    assert registry.tools["core.echo"].category == "core"
    assert registry.tools["plugin.note"].resource_target_kind == "candidate"
    assert "read_memory" in registry.tools


def test_toolbus_sync_execute_works_inside_running_event_loop() -> None:
    registry = ToolRegistry()
    token = CancellationToken()

    async def _async_handler(arguments: dict[str, object], *, cancel_token: CancellationToken | None = None) -> dict[str, object]:
        assert cancel_token is token
        return {"echo": arguments}

    registry.register(
        ToolDefinition(
            name="core.echo",
            description="Echo content.",
            parameters={"type": "object"},
            handler=_async_handler,
        )
    )

    async def _scenario():
        return registry.execute("core.echo", {"value": 1}, cancel_token=token)

    result = asyncio.run(_scenario())

    assert result.is_error is False
    assert result.output == {"echo": {"value": 1}}


def test_register_core_tools_do_not_expose_skill_execution_tool() -> None:
    registry = ToolRegistry()
    register_core_tools(registry)

    assert "read_memory" in registry.tools
    assert all(tool.resource_target_kind != "skill" for tool in registry.tools.values())
    assert all(tool.metadata.get("resource_target_kind") != "skill" for tool in registry.to_agent_runtime_tools())


def test_core_read_memory_tool_uses_memory_service(tmp_path: Path) -> None:
    settings = AppSettings(
        data_dir=str(tmp_path / "data"),
        database_url=f"sqlite:///{tmp_path / 'memory-tool.db'}",
    )
    engine = create_engine_from_settings(settings)
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        profile = RecruitAgentProfile(agent_key="primary", name="Primary", is_primary=True)
        candidate = Candidate(name="Alice")
        session.add_all([profile, candidate])
        session.commit()
        MemoryService(session).write(
            scope_kind="candidate",
            scope_ref=candidate.id,
            agent_profile_id=profile.id,
            memory_item_id="alice-status",
            kind="candidate_fact",
            index_name="status",
            index_description="Alice replied",
            summary="Alice replied",
            content={"status": "replied"},
        )
        candidate_id = candidate.id

    output = _build_read_memory_handler(session_factory)({"scope_kind": "candidate", "scope_ref": candidate_id})

    assert output["count"] == 1
    assert output["entries"][0]["memory_item_id"] == "alice-status"


def test_core_record_learning_tool_queues_learning(tmp_path: Path) -> None:
    settings = AppSettings(
        data_dir=str(tmp_path / "data"),
        database_url=f"sqlite:///{tmp_path / 'learning-tool.db'}",
    )
    engine = create_engine_from_settings(settings)
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    output = _build_record_learning_handler(session_factory)(
        {"kind": "prompt_lesson", "payload": {"content": "Prefer verified candidate facts.", "tags": ["memory"]}}
    )

    assert output["queued"] is True
    assert output["learning_id"]


def test_scene_context_tool_detection_covers_computer_capabilities() -> None:
    browser_like = ToolDefinition(
        name="hid.semantic_action",
        description="Computer action",
        parameters={"type": "object"},
        handler=lambda arguments: arguments,
        metadata={"external_tool": True, "real_environment": True, "capabilities": ["computer", "computer_write"]},
    )

    assert is_scene_context_tool(browser_like) is True


def test_delegate_scene_context_tool_schema_mentions_browser_computer_contracts() -> None:
    tool = build_delegate_scene_context_tool(lambda arguments: arguments)
    properties = tool.parameters["properties"]

    assert "artifact_expectations" in properties["output_contract"]["description"]
    assert "browser_locate_download" in properties["output_contract"]["description"]
    assert "business_writeback" in properties["output_contract"]["description"]
    assert "attach_resume_artifact" in properties["output_contract"]["description"]
    assert "browser_target" in properties["environment_requirements"]["description"]
    assert "structured fields" in properties["environment_requirements"]["description"]
    assert "browser_target" in properties
    assert "artifact_expectations" in properties
    assert "candidate landing regions" in properties["context"]["description"]
