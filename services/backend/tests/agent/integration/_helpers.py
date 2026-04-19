from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from scene_pilot.agents.assistant import AssistantAgent
from scene_pilot.api.routers.assistant import build_router as build_assistant_router
from scene_pilot.core.settings import AppSettings
from scene_pilot.db.session import create_engine_from_settings, create_session_factory, initialize_database
from scene_pilot.kernel.kernel import AgentKernel
from scene_pilot.plugins.host import PluginHost
from scene_pilot.runtime.providers import LLMProvider
from scene_pilot.runtime.tools import ToolRegistry, register_core_tools
from scene_pilot.assistant.session_store import AssistantSessionStore


def make_session_factory(tmp_path: Path, db_name: str) -> sessionmaker[Session]:
    settings = AppSettings(
        data_dir=str(tmp_path / "data"),
        database_url=f"sqlite:///{tmp_path / db_name}",
    )
    engine = create_engine_from_settings(settings)
    initialize_database(engine)
    return create_session_factory(engine)


def make_session(tmp_path: Path, db_name: str) -> Session:
    return make_session_factory(tmp_path, db_name)()


def build_assistant_client(
    tmp_path: Path,
    *,
    provider: LLMProvider,
    tools: ToolRegistry | None = None,
    plugin_host: PluginHost | None = None,
) -> tuple[TestClient, AssistantAgent, sessionmaker[Session]]:
    session_factory = make_session_factory(tmp_path, "assistant.db")
    registry = tools or ToolRegistry()
    if not registry.tools:
        register_core_tools(registry)
    kernel = AgentKernel(
        provider=provider,
        tool_registry=registry,
        plugin_host=plugin_host or PluginHost(),
    )
    store = AssistantSessionStore(session_factory=session_factory, base_dir=tmp_path / "assistant-jsonl")
    agent = AssistantAgent(kernel=kernel, session_factory=session_factory, session_store=store)
    app = FastAPI()
    app.include_router(build_assistant_router(agent))
    return TestClient(app), agent, session_factory
