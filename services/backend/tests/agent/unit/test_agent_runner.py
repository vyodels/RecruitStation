from __future__ import annotations

from agent_runtime.fixtures import LLMResponse, ScriptedProvider, ToolCall

from recruit_station.capabilities.tools import ToolDefinition, ToolRegistry
from recruit_station.agents.autonomous import _final_output_continuation_resolver
from recruit_station.product_adapters.agent_runner import run_agent_turn
from recruit_station.product_adapters.context_builder import build_assistant_turn_context, build_autonomous_turn_context
from recruit_station.product_adapters.result_semantics import extract_execution_status


def test_runner_places_adapter_system_prompt_outside_messages_for_both_agent_kinds() -> None:
    assistant_provider = ScriptedProvider(provider_name="assistant-scripted", responses=[LLMResponse(content="assistant done")])
    autonomous_provider = ScriptedProvider(provider_name="autonomous-scripted", responses=[LLMResponse(content="autonomous done")])
    assistant_context = build_assistant_turn_context(
        history_messages=[],
        user_message="hello",
        system_prompt="Assistant shared prompt.",
    )
    autonomous_context = build_autonomous_turn_context(
        title="Run",
        instruction="Do work",
        system_prompt="Autonomous shared prompt.",
        scope_kind="global",
        scope_ref="workspace",
        constraints={},
        world_snapshot={},
        recent_events=[],
        memory_entries=[],
        available_tools=[],
        skill_contexts=[],
        available_mcps=[],
    )

    run_agent_turn(
        provider=assistant_provider,
        tool_registry=ToolRegistry(),
        agent_definition_id=None,
        conversation_id="assistant-conv",
        initial_messages=assistant_context.initial_messages,
        turn_input=assistant_context.turn_input,
        max_llm_invocations=1,
    )
    run_agent_turn(
        provider=autonomous_provider,
        tool_registry=ToolRegistry(),
        agent_definition_id=None,
        conversation_id="autonomous-conv",
        initial_messages=autonomous_context.initial_messages,
        turn_input=autonomous_context.turn_input,
        max_llm_invocations=1,
    )

    assistant_request = assistant_provider.captured_requests[0]
    autonomous_request = autonomous_provider.captured_requests[0]
    assert assistant_request.system_prompt == str(assistant_context.initial_messages[0].content)
    assert autonomous_request.system_prompt == str(autonomous_context.initial_messages[0].content)
    assert all(message.role != "system" for message in assistant_request.messages)
    assert all(message.role != "system" for message in autonomous_request.messages)


def test_extract_execution_status_prefers_execution_status_over_business_status() -> None:
    assert extract_execution_status({"status": "pass", "execution_status": "completed"}) == "completed"


def test_runner_can_resolve_terminal_status_from_final_output_text() -> None:
    provider = ScriptedProvider(provider_name="autonomous-scripted", responses=[LLMResponse(content="结果：已阻塞，等待恢复。")])

    result = run_agent_turn(
        provider=provider,
        tool_registry=ToolRegistry(),
        agent_definition_id=None,
        conversation_id="autonomous-conv",
        initial_messages=[],
        turn_input="run",
        max_llm_invocations=1,
        final_output_status_resolver=lambda text: ("escalate", "escalate") if "已阻塞" in text else None,
    )

    assert result.status == "escalate"
    assert result.gate_signal == "escalate"
    assert result.final_output == "结果：已阻塞，等待恢复。"


def test_runner_can_reject_final_output_and_continue_with_tool_call() -> None:
    provider = ScriptedProvider(
        provider_name="autonomous-scripted",
        responses=[
            LLMResponse(content="结果：未完成全量 JD 同步，当前阻塞。"),
            LLMResponse(
                tool_calls=[ToolCall(id="tool-1", name="test.observe", arguments={"scope": "remaining-jobs"})],
                finish_reason="tool_calls",
            ),
            LLMResponse(content="JD sync completed.", result_data={"execution_status": "completed"}),
        ],
    )
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="test.observe",
            description="Observe remaining jobs.",
            parameters={"type": "object", "additionalProperties": True},
            handler=lambda arguments: {"observed": arguments.get("scope")},
            category="core",
        )
    )

    result = run_agent_turn(
        provider=provider,
        tool_registry=registry,
        agent_definition_id=None,
        conversation_id="autonomous-conv",
        initial_messages=[],
        turn_input="run",
        max_llm_invocations=3,
        structured_status_resolver=lambda value: ("complete", "run_done")
        if extract_execution_status(value) == "completed"
        else None,
        final_output_status_resolver=lambda text: ("escalate", "escalate") if "阻塞" in text else None,
        final_output_continuation_resolver=lambda text, tool_calls, tool_results, attempt: "continue with tools"
        if "未完成全量" in text and not tool_calls and attempt == 0
        else None,
    )

    assert result.status == "complete"
    assert result.gate_signal == "run_done"
    assert result.final_output == "JD sync completed."
    assert any(call.get("tool_name") == "test.observe" for call in result.tool_calls)
    assert provider.captured_requests[1].messages[-1].content == "continue with tools"


def test_jd_sync_continuation_rejects_partial_final_output_after_tool_calls() -> None:
    resolver = _final_output_continuation_resolver(agent_kind="jd_sync")
    assert resolver is not None

    continuation = resolver(
        "已完成部分 JD 同步，但未完成全量详情读取，当前 partial。",
        [{"tool_name": "delegate_scene_context"}],
        [{"tool_name": "delegate_scene_context", "result": {"status": "partial"}}],
        0,
    )

    assert continuation is not None
    assert "即使本轮已经调用过 scene 或业务工具" in continuation
    assert "继续同一个 turn" in continuation


def test_jd_sync_continuation_rejects_bland_final_output_when_result_data_is_partial() -> None:
    resolver = _final_output_continuation_resolver(agent_kind="jd_sync")
    assert resolver is not None

    continuation = resolver(
        "已处理。",
        [{"tool_name": "delegate_scene_context"}],
        [{"tool_name": "delegate_scene_context", "result": {"status": "partial"}}],
        0,
        {"status": "partial", "remaining_jobs": ["jd-solution-002"]},
    )

    assert continuation is not None
    assert "继续同一个 turn" in continuation


def test_jd_sync_continuation_treats_hid_frontmost_timeout_as_recoverable_after_tool_calls() -> None:
    resolver = _final_output_continuation_resolver(agent_kind="jd_sync")
    assert resolver is not None

    continuation = resolver(
        "本轮同步阻塞，未完成全量 JD 同步。阻塞原因：E_TIMEOUT: injector action exceeded timeout；"
        "E_NOT_FRONTMOST: target app is not frontmost；VirtualHID/电脑执行链路不可用。剩余 4 个职位未完成详情读取。",
        [{"tool_name": "delegate_scene_context"}],
        [{"tool_name": "delegate_scene_context", "result": {"status": "partial"}}],
        0,
        {},
    )

    assert continuation is not None
    assert "E_TIMEOUT" in continuation
    assert "继续同一个 turn" in continuation


def test_jd_sync_continuation_treats_nested_pending_confirmation_as_recoverable() -> None:
    resolver = _final_output_continuation_resolver(agent_kind="jd_sync")
    assert resolver is not None

    continuation = resolver(
        "仍需人工恢复，当前 blocked。原因包含 human-only / pending_confirmation / E_NOT_FRONTMOST / "
        "E_DAEMON_UNREACHABLE。剩余 4 个 JD 未完成详情读取。",
        [{"tool_name": "delegate_scene_context"}],
        [{"tool_name": "delegate_scene_context", "result": {"status": "blocked", "blockers": ["pending_confirmation"]}}],
        0,
        {},
    )

    assert continuation is not None
    assert "pending_confirmation" in continuation
    assert "继续同一个 turn" in continuation


def test_jd_sync_continuation_allows_real_login_boundary_to_stop() -> None:
    resolver = _final_output_continuation_resolver(agent_kind="jd_sync")
    assert resolver is not None

    continuation = resolver(
        "本轮阻塞，未完成全量 JD 同步。目标页面要求重新登录和验证码，无法继续读取剩余详情。",
        [{"tool_name": "delegate_scene_context"}],
        [{"tool_name": "delegate_scene_context", "result": {"status": "blocked"}}],
        0,
        {},
    )

    assert continuation is None
