"""Helpers for constructing agent-wallet providers without direct wallet imports."""

from __future__ import annotations

from typing import Any


async def create_tron_provider(
    *,
    private_key: str | None = None,
    rpc_url: str | None = None,
    api_key: str | None = None,
    keystore_path: str | None = None,
    keystore_password: str | None = None,
) -> Any:
    """Create an agent-wallet TronProvider via async ``create()`` factory."""
    from wallet import TronProvider

    return await TronProvider.create(
        rpc_url=rpc_url,
        private_key=private_key,
        api_key=api_key,
        keystore_path=keystore_path,
        keystore_password=keystore_password,
    )


async def create_flash_provider(
    *,
    rpc_url: str | None = None,
    api_key: str | None = None,
    privy_app_id: str | None = None,
    privy_app_secret: str | None = None,
    wallet_id: str | None = None,
    keystore_path: str | None = None,
    keystore_password: str | None = None,
) -> Any:
    """Create an agent-wallet FlashProvider via async ``create()`` factory."""
    from wallet import FlashProvider

    return await FlashProvider.create(
        rpc_url=rpc_url,
        api_key=api_key,
        privy_app_id=privy_app_id,
        privy_app_secret=privy_app_secret,
        wallet_id=wallet_id,
        keystore_path=keystore_path,
        keystore_password=keystore_password,
    )
