from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import AgentResult, LLMUsage, Message, ToolCall
from .prompts import PromptBuilder
from .providers import LLMProvider
from .result_semantics import normalize_result_payload
from .tools import ToolRegistry


@dataclass(slots=True)
class AgentLoopConfig:
    max_turns: int = 8
    token_budget: int = 8_192
    preferred_provider: str | None = None


@dataclass(slots=True)
class AgentLoop:
    provider: LLMProvider
    tools: ToolRegistry
    prompt_builder: PromptBuilder = field(default_factory=PromptBuilder)
    config: AgentLoopConfig = field(default_factory=AgentLoopConfig)

    def run(
        self,
        task: Any,
        *,
        session: dict[str, Any] | None = None,
        skill: dict[str, Any] | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> AgentResult:
        messages = self.prompt_builder.build_messages(
            task,
            session=session,
            skill=skill,
            extra_context=extra_context,
        )
        token_budget = getattr(task, "token_budget", None) or self.config.token_budget
        max_turns = getattr(task, "max_turns", None) or self.config.max_turns
        usage = LLMUsage()
        tool_outputs = []

        for turn in range(max_turns):
            response = self.provider.generate(
                messages,
                tools=self.tools.describe(),
                task={
                    "task_type": getattr(task, "task_type", None),
                    "payload": getattr(task, "payload", {}) or {},
                },
            )
            usage.prompt_tokens += response.usage.prompt_tokens
            usage.completion_tokens += response.usage.completion_tokens
            usage.total_tokens += response.usage.total_tokens

            if usage.total_tokens > token_budget:
                return AgentResult(
                    success=False,
                    status="timeout",
                    content="Token budget exceeded",
                    messages=messages,
                    usage=usage,
                    tool_outputs=tool_outputs,
                )

            if response.requires_human_input:
                return AgentResult(
                    success=False,
                    status="waiting_human",
                    content=response.content,
                    messages=messages,
                    usage=usage,
                    tool_outputs=tool_outputs,
                )

            if response.tool_calls:
                messages.append(
                    Message(
                        role="assistant",
                        content=response.content or "",
                        metadata={"tool_calls": [tool_call.to_provider_payload() for tool_call in response.tool_calls]},
                    )
                )
                submitted_result: tuple[dict[str, Any], dict[str, Any] | None] | None = None
                for tool_call in response.tool_calls:
                    result = self.tools.execute(tool_call.name, tool_call.arguments)
                    tool_outputs.append(result)
                    if self._is_terminal_result_submission(tool_call, result.output, result.is_error):
                        submitted_result = self._normalize_submitted_result(tool_call, result.output)
                    messages.append(
                        Message(
                            role="tool",
                            content=result.to_message_content(),
                            name=tool_call.name,
                            tool_call_id=tool_call.id,
                            metadata={"is_error": result.is_error},
                        )
                    )
                if submitted_result is not None:
                    result_data, skill_draft = submitted_result
                    return AgentResult(
                        success=True,
                        status="completed",
                        content=response.content,
                        data=result_data,
                        skill_draft=skill_draft,
                        messages=messages,
                        usage=usage,
                        tool_outputs=tool_outputs,
                    )
                continue

            if response.result_data is not None:
                messages.append(Message(role="assistant", content=response.content or ""))
                result_data, _ = normalize_result_payload(response.result_data)
                return AgentResult(
                    success=True,
                    status="completed",
                    content=response.content,
                    data=result_data,
                    skill_draft=response.skill_draft,
                    messages=messages,
                    usage=usage,
                    tool_outputs=tool_outputs,
                )

            if response.finish_reason in {"stop", "completed", "result"} and response.content:
                messages.append(Message(role="assistant", content=response.content))
                return AgentResult(
                    success=True,
                    status="completed",
                    content=response.content,
                    messages=messages,
                    usage=usage,
                    tool_outputs=tool_outputs,
                )

            messages.append(
                Message(
                    role="user",
                    content="Please continue. If the task is complete, submit the structured result.",
                )
            )

        return AgentResult(
            success=False,
            status="timeout",
            content="Max turns reached",
            messages=messages,
            usage=usage,
            tool_outputs=tool_outputs,
        )

    def _is_terminal_result_submission(
        self,
        tool_call: ToolCall,
        output: Any,
        is_error: bool,
    ) -> bool:
        if is_error:
            return False
        tool = self.tools.tools.get(tool_call.name)
        if tool is None:
            return False
        if tool.metadata.get("terminal_result_submission"):
            return True
        return tool_call.name == "submit_result"

    def _normalize_submitted_result(
        self,
        tool_call: ToolCall,
        output: Any,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        if isinstance(output, dict) and isinstance(output.get("payload"), dict):
            payload = dict(output["payload"])
        else:
            payload = dict(tool_call.arguments or {})
        return normalize_result_payload(payload)


def run_agent_loop(
    provider: LLMProvider,
    tools: ToolRegistry,
    task: Any,
    *,
    prompt_builder: PromptBuilder | None = None,
    config: AgentLoopConfig | None = None,
    session: dict[str, Any] | None = None,
    skill: dict[str, Any] | None = None,
    extra_context: dict[str, Any] | None = None,
) -> AgentResult:
    loop = AgentLoop(
        provider=provider,
        tools=tools,
        prompt_builder=prompt_builder or PromptBuilder(),
        config=config or AgentLoopConfig(),
    )
    return loop.run(task, session=session, skill=skill, extra_context=extra_context)
