from __future__ import annotations

import pytest

from scene_pilot.core.settings import AppSettings
from scene_pilot.runtime.models import Message
from scene_pilot.runtime.providers import ProviderError
from scene_pilot.services.container import AppContainer


def test_functional_closure_real_provider_path_is_not_fake_default(tmp_path) -> None:
    container = AppContainer.build(
        AppSettings(
            data_dir=str(tmp_path / "data"),
            database_url=f"sqlite:///{tmp_path / 'functional-provider.db'}",
            provider_config={},
        )
    )
    assert container.provider.provider_name == "unavailable"
    with pytest.raises(ProviderError):
        container.provider.generate([Message(role="user", content="ping")])
