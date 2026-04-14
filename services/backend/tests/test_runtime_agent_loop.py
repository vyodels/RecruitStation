from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
import unittest


SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from recruit_agent.runtime.agent_loop import AgentLoop, AgentLoopConfig
from recruit_agent.runtime.models import LLMResponse, ToolCall
from recruit_agent.runtime.providers import ScriptedProvider
from recruit_agent.runtime.tools import ToolDefinition, ToolRegistry


class AgentLoopTests(unittest.TestCase):
    def test_tool_call_then_result_submission(self) -> None:
        provider = ScriptedProvider(
            provider_name="scripted",
            responses=[
                LLMResponse(
                    content="use tool",
                    tool_calls=[ToolCall(id="1", name="echo", arguments={"value": "alpha"})],
                ),
                LLMResponse(
                    content="final",
                    result_data={"status": "passed", "score": 88},
                ),
            ],
        )
        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="echo",
                description="Echo args",
                parameters={"type": "object"},
                handler=lambda args: {"echoed": args["value"]},
            )
        )
        loop = AgentLoop(provider=provider, tools=registry, config=AgentLoopConfig(max_turns=4, token_budget=100))
        task = SimpleNamespace(task_type="initial_screening", payload={"jd_criteria": "Python"})

        result = loop.run(task)

        self.assertTrue(result.success)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.data["status"], "pass")
        self.assertEqual(len(result.tool_outputs), 1)
        self.assertEqual(result.tool_outputs[0].output["echoed"], "alpha")

    def test_waiting_human_response(self) -> None:
        provider = ScriptedProvider(
            provider_name="scripted",
            responses=[LLMResponse(content="need review", requires_human_input=True)],
        )
        registry = ToolRegistry()
        loop = AgentLoop(provider=provider, tools=registry)
        task = SimpleNamespace(task_type="initial_screening", payload={"jd_criteria": "Python"})

        result = loop.run(task)
        self.assertFalse(result.success)
        self.assertEqual(result.status, "waiting_human")

    def test_submit_result_tool_call_finishes_with_structured_data(self) -> None:
        provider = ScriptedProvider(
            provider_name="scripted",
            responses=[
                LLMResponse(
                    content="submitting structured result",
                    tool_calls=[
                        ToolCall(
                            id="submit-1",
                            name="submit_result",
                            arguments={
                                "status": "pass",
                                "data": {"score": 91, "summary": "Strong signal"},
                            },
                        )
                    ],
                )
            ],
        )
        registry = ToolRegistry()
        registry.register(registry.build_result_submission_tool())
        loop = AgentLoop(provider=provider, tools=registry)
        task = SimpleNamespace(task_type="initial_screening", payload={"jd_criteria": "Python"})

        result = loop.run(task)

        self.assertTrue(result.success)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.data["status"], "pass")
        self.assertEqual(result.data["score"], 91)
        self.assertEqual(result.tool_outputs[0].output["payload"]["status"], "pass")

    def test_tool_call_history_preserves_assistant_tool_calls(self) -> None:
        provider = ScriptedProvider(
            provider_name="scripted",
            responses=[
                LLMResponse(
                    content="use tool",
                    tool_calls=[ToolCall(id="echo-1", name="echo", arguments={"value": "alpha"})],
                ),
                LLMResponse(
                    content="final",
                    result_data={"status": "passed", "score": 88},
                ),
            ],
        )
        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="echo",
                description="Echo args",
                parameters={"type": "object"},
                handler=lambda args: {"echoed": args["value"]},
            )
        )
        loop = AgentLoop(provider=provider, tools=registry, config=AgentLoopConfig(max_turns=4, token_budget=100))
        task = SimpleNamespace(task_type="initial_screening", payload={"jd_criteria": "Python"})

        result = loop.run(task)

        assistant_with_tool_call = next(message for message in result.messages if message.role == "assistant" and message.metadata.get("tool_calls"))
        self.assertEqual(assistant_with_tool_call.metadata["tool_calls"][0]["function"]["name"], "echo")
        tool_message = next(message for message in result.messages if message.role == "tool")
        self.assertEqual(tool_message.tool_call_id, "echo-1")

    def test_submit_result_flattens_nested_screening_result(self) -> None:
        provider = ScriptedProvider(
            provider_name="scripted",
            responses=[
                LLMResponse(
                    content="submitting nested screening result",
                    tool_calls=[
                        ToolCall(
                            id="submit-2",
                            name="submit_result",
                            arguments={
                                "status": "completed",
                                "result": {
                                    "screening_decision": "pass",
                                    "summary": "Strong frontend signal",
                                },
                            },
                        )
                    ],
                )
            ],
        )
        registry = ToolRegistry()
        registry.register(registry.build_result_submission_tool())
        loop = AgentLoop(provider=provider, tools=registry)
        task = SimpleNamespace(task_type="initial_screening", payload={"jd_criteria": "Python"})

        result = loop.run(task)

        self.assertTrue(result.success)
        self.assertEqual(result.data["status"], "pass")
        self.assertEqual(result.data["screening_decision"], "pass")
        self.assertEqual(result.data["summary"], "Strong frontend signal")

    def test_submit_result_promotes_decision_to_status(self) -> None:
        provider = ScriptedProvider(
            provider_name="scripted",
            responses=[
                LLMResponse(
                    content="submitting decision result",
                    tool_calls=[
                        ToolCall(
                            id="submit-3",
                            name="submit_result",
                            arguments={
                                "status": "completed",
                                "result": {
                                    "decision": "pass",
                                    "summary": "Advance candidate",
                                },
                            },
                        )
                    ],
                )
            ],
        )
        registry = ToolRegistry()
        registry.register(registry.build_result_submission_tool())
        loop = AgentLoop(provider=provider, tools=registry)
        task = SimpleNamespace(task_type="initial_screening", payload={"jd_criteria": "Python"})

        result = loop.run(task)

        self.assertTrue(result.success)
        self.assertEqual(result.data["status"], "pass")
        self.assertEqual(result.data["decision"], "pass")

    def test_submit_result_promotes_nested_screening_result_decision(self) -> None:
        provider = ScriptedProvider(
            provider_name="scripted",
            responses=[
                LLMResponse(
                    content="submitting nested decision result",
                    tool_calls=[
                        ToolCall(
                            id="submit-4",
                            name="submit_result",
                            arguments={
                                "status": "completed",
                                "result": {
                                    "screening_result": {
                                        "decision": "pass",
                                        "summary": "Advance candidate",
                                    }
                                },
                            },
                        )
                    ],
                )
            ],
        )
        registry = ToolRegistry()
        registry.register(registry.build_result_submission_tool())
        loop = AgentLoop(provider=provider, tools=registry)
        task = SimpleNamespace(task_type="initial_screening", payload={"jd_criteria": "Python"})

        result = loop.run(task)

        self.assertTrue(result.success)
        self.assertEqual(result.data["status"], "pass")
        self.assertEqual(result.data["screening_result"]["decision"], "pass")

    def test_submit_result_promotes_top_level_screening_result_decision(self) -> None:
        provider = ScriptedProvider(
            provider_name="scripted",
            responses=[
                LLMResponse(
                    content="submitting provider-shaped result",
                    tool_calls=[
                        ToolCall(
                            id="submit-5",
                            name="submit_result",
                            arguments={
                                "status": "completed",
                                "screening_result": {
                                    "decision": "pass",
                                    "summary": "Advance candidate",
                                },
                            },
                        )
                    ],
                )
            ],
        )
        registry = ToolRegistry()
        registry.register(registry.build_result_submission_tool())
        loop = AgentLoop(provider=provider, tools=registry)
        task = SimpleNamespace(task_type="initial_screening", payload={"jd_criteria": "Python"})

        result = loop.run(task)

        self.assertTrue(result.success)
        self.assertEqual(result.data["status"], "pass")
        self.assertEqual(result.data["execution_status"], "completed")
        self.assertEqual(result.data["screening_result"]["decision"], "pass")

    def test_submit_result_promotes_top_level_screening_result_decision(self) -> None:
        provider = ScriptedProvider(
            provider_name="scripted",
            responses=[
                LLMResponse(
                    content="submitting top-level screening result",
                    tool_calls=[
                        ToolCall(
                            id="submit-5",
                            name="submit_result",
                            arguments={
                                "status": "completed",
                                "screening_result": {
                                    "decision": "pass",
                                    "summary": "Advance candidate",
                                },
                            },
                        )
                    ],
                )
            ],
        )
        registry = ToolRegistry()
        registry.register(registry.build_result_submission_tool())
        loop = AgentLoop(provider=provider, tools=registry)
        task = SimpleNamespace(task_type="initial_screening", payload={"jd_criteria": "Python"})

        result = loop.run(task)

        self.assertTrue(result.success)
        self.assertEqual(result.data["status"], "pass")
        self.assertEqual(result.data["screening_result"]["decision"], "pass")

    def test_direct_result_data_promotes_nested_screening_result_decision(self) -> None:
        provider = ScriptedProvider(
            provider_name="scripted",
            responses=[
                LLMResponse(
                    content="direct result payload",
                    result_data={
                        "status": "completed",
                        "screening_result": {
                            "decision": "pass",
                            "summary": "Advance candidate",
                        },
                    },
                )
            ],
        )
        loop = AgentLoop(provider=provider, tools=ToolRegistry())
        task = SimpleNamespace(task_type="initial_screening", payload={"jd_criteria": "Python"})

        result = loop.run(task)

        self.assertTrue(result.success)
        self.assertEqual(result.data["status"], "pass")
        self.assertEqual(result.data["execution_status"], "completed")
        self.assertEqual(result.data["screening_result"]["decision"], "pass")


if __name__ == "__main__":
    unittest.main()
