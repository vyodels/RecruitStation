from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from scene_pilot.agents.assistant import AssistantAgent
from scene_pilot.agents.autonomous import AutonomousAgent
from scene_pilot.agents.heartbeat import Heartbeat
from scene_pilot.assistant.session_store import AssistantSessionStore
from scene_pilot.core.settings import AppSettings, load_settings
from scene_pilot.db.session import create_engine_from_settings, create_session_factory, initialize_database
from scene_pilot.evolution.learning_writer import LearningWriter
from scene_pilot.evolution.promotion import PromotionService
from scene_pilot.evolution.queue import EvolutionQueue
from scene_pilot.execution_units.browser_worker import run_browser_worker
from scene_pilot.execution_units.runner import ExecutionUnitRunner
from scene_pilot.execution_units.store import ExecutionUnitStore
from scene_pilot.kernel.kernel import AgentKernel
from scene_pilot.plugins.host import PluginHost
from scene_pilot.plugins.loader import install_manifest
from scene_pilot.plugins.recruit.manifest import RecruitPluginManifest
from scene_pilot.runtime.providers import (
    AnthropicProvider,
    LLMProvider,
    OpenAICompatibleProvider,
    ProviderRegistry,
    ProviderRegistryAdapter,
    UnavailableProvider,
)
from scene_pilot.runtime.tools import ToolRegistry, register_core_tools
from scene_pilot.scheduler.queue import SqlAlchemyQueue
from scene_pilot.scheduler.scheduler import SerialScheduler
from scene_pilot.services.dashboard import DashboardService
from scene_pilot.services.events import EventStreamService
from scene_pilot.services.feature_flags import FeatureFlagService
from scene_pilot.services.mcp_registry import McpRegistryService
from scene_pilot.services.sync import SyncService
from scene_pilot.services.system_commands import SystemCommandService


@dataclass(slots=True)
class AppContainer:
    settings: AppSettings
    session_factory: sessionmaker[Session]
    provider: LLMProvider
    providers: ProviderRegistry
    tool_registry: ToolRegistry
    plugin_host: PluginHost
    kernel: AgentKernel
    autonomous_agent: AutonomousAgent
    heartbeat: Heartbeat
    session_store: AssistantSessionStore
    assistant_agent: AssistantAgent
    execution_unit_store: ExecutionUnitStore
    execution_unit_runner: ExecutionUnitRunner
    learning_writer: LearningWriter
    evolution_queue: EvolutionQueue
    promotion: PromotionService
    mcp_registry: McpRegistryService
    events: EventStreamService
    flags: FeatureFlagService
    system_commands: SystemCommandService
    sync: SyncService
    dashboard: DashboardService
    scheduler: SerialScheduler

    @classmethod
    def build(cls, settings: AppSettings | None = None) -> "AppContainer":
        resolved_settings = settings or load_settings()
        engine = create_engine_from_settings(resolved_settings)
        initialize_database(engine)
        session_factory = create_session_factory(engine)

        providers, provider = _build_provider_bundle(resolved_settings)
        tool_registry = ToolRegistry()
        register_core_tools(tool_registry)

        plugin_host = PluginHost()
        install_manifest(plugin_host, RecruitPluginManifest(session_factory))
        tool_registry.merge(plugin_host.tool_registry)

        learning_writer = LearningWriter(session_factory)
        kernel = AgentKernel(
            provider=provider,
            tool_registry=tool_registry,
            plugin_host=plugin_host,
            learning_writer=learning_writer,
        )
        autonomous_agent = AutonomousAgent(session_factory=session_factory, kernel=kernel)
        heartbeat = Heartbeat(session_factory=session_factory, autonomous_agent=autonomous_agent)

        data_dir = resolved_settings.resolved_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        session_store = AssistantSessionStore(session_factory=session_factory, base_dir=Path(data_dir) / "assistant-jsonl")
        assistant_agent = AssistantAgent(kernel=kernel, session_factory=session_factory, session_store=session_store)

        execution_unit_store = ExecutionUnitStore()
        execution_unit_runner = ExecutionUnitRunner(
            store=execution_unit_store,
            workers={"browser": run_browser_worker},
        )
        evolution_queue = EvolutionQueue(session_factory)
        promotion = PromotionService(session_factory)
        events = EventStreamService()
        flags = _build_flags(resolved_settings)
        sync = _build_sync_service(resolved_settings, session_factory)
        dashboard = DashboardService(settings=resolved_settings, events=events, sync_service=sync)
        scheduler = SerialScheduler(queue=SqlAlchemyQueue(session_factory))
        system_commands = SystemCommandService(
            session_factory=session_factory,
            flags=flags,
            events=events,
            execution_enabled=resolved_settings.feature_flags.enable_system_commands,
        )
        mcp_registry = McpRegistryService(session_factory)
        return cls(
            settings=resolved_settings,
            session_factory=session_factory,
            provider=provider,
            providers=providers,
            tool_registry=tool_registry,
            plugin_host=plugin_host,
            kernel=kernel,
            autonomous_agent=autonomous_agent,
            heartbeat=heartbeat,
            session_store=session_store,
            assistant_agent=assistant_agent,
            execution_unit_store=execution_unit_store,
            execution_unit_runner=execution_unit_runner,
            learning_writer=learning_writer,
            evolution_queue=evolution_queue,
            promotion=promotion,
            mcp_registry=mcp_registry,
            events=events,
            flags=flags,
            system_commands=system_commands,
            sync=sync,
            dashboard=dashboard,
            scheduler=scheduler,
        )

    def reload_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        self.providers, self.provider = _build_provider_bundle(settings)
        self.kernel.provider = self.provider
        self.dashboard.settings = settings

        self.flags.flags.clear()
        self.flags.merge(
            {
                "skills.system_command": settings.feature_flags.enable_system_commands,
                "skills.auto_activate": bool(settings.provider_config.get("skills_auto_activate", False)),
            }
        )

        self.sync.intranet_enabled = settings.feature_flags.enable_intranet_sync
        self.sync.target = _build_sync_target(settings)
        self.system_commands.execution_enabled = settings.feature_flags.enable_system_commands


def _build_provider_bundle(settings: AppSettings) -> tuple[ProviderRegistry, LLMProvider]:
    registry = ProviderRegistry()
    runtime_settings = settings.provider_runtime_settings()
    if runtime_settings.openai_api_key:
        registry.register(OpenAICompatibleProvider(settings.build_provider_config("openai")))
    if runtime_settings.anthropic_api_key:
        registry.register(AnthropicProvider(settings.build_provider_config("anthropic")))
    if registry.providers:
        preferred = registry.fallback_order[0]
        return registry, ProviderRegistryAdapter(registry=registry, preferred_provider=preferred)
    return registry, UnavailableProvider(
        reason="provider unavailable: configure RECRUIT_AGENT_PROVIDER_CONFIG__OPENAI_API_KEY or RECRUIT_AGENT_PROVIDER_CONFIG__ANTHROPIC_API_KEY",
    )


def _build_flags(settings: AppSettings) -> FeatureFlagService:
    flags = FeatureFlagService()
    flags.merge(
        {
            "skills.system_command": settings.feature_flags.enable_system_commands,
            "skills.auto_activate": bool(settings.provider_config.get("skills_auto_activate", False)),
        }
    )
    return flags


def _build_sync_target(settings: AppSettings) -> dict[str, Any]:
    return {
        "kind": "intranet",
        "base_url": settings.intranet_sync.base_url,
        "api_path": settings.intranet_sync.api_path,
    }


def _build_sync_service(settings: AppSettings, session_factory: sessionmaker[Session]) -> SyncService:
    return SyncService(
        intranet_enabled=settings.feature_flags.enable_intranet_sync,
        session_factory=session_factory,
        target=_build_sync_target(settings),
    )
