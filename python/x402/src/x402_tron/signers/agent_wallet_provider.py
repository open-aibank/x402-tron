"""Helpers for constructing agent-wallet providers without direct wallet imports."""

from __future__ import annotations

from typing import Any


async def create_tron_provider(
    *,
    keystore_path: str | None = None,
) -> Any:
    """Create an agent-wallet TronProvider via async ``create()`` factory."""
    from wallet import TronProvider

    return await TronProvider.create(
        keystore_path=keystore_path,
    )
