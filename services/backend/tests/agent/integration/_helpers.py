from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from recruit_station.agents.assistant import AssistantAdapter
from recruit_station.api.routers.assistant import build_router as build_assistant_router
from recruit_station.core.settings import AppSettings
from recruit_station.db.session import create_engine_from_settings, create_session_factory, initialize_database
from recruit_station.plugins.host import PluginHost
from recruit_station.agent_runtime.providers import LLMProvider
from recruit_station.capabilities.tools import ToolRegistry, register_core_tools
from recruit_station.assistant.session_store import AssistantSessionStore


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
) -> tuple[TestClient, AssistantAdapter, sessionmaker[Session]]:
    session_factory = make_session_factory(tmp_path, "assistant.db")
    registry = tools or ToolRegistry()
    if not registry.tools:
        register_core_tools(registry)
    store = AssistantSessionStore(session_factory=session_factory, base_dir=tmp_path / "assistant-jsonl")
    agent = AssistantAdapter(
        provider=provider,
        tool_registry=registry,
        plugin_host=plugin_host or PluginHost(),
        session_factory=session_factory,
        session_store=store,
    )
    app = FastAPI()
    app.include_router(build_assistant_router(agent))
    return TestClient(app), agent, session_factory
