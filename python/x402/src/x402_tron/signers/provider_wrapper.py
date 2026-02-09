"""
Provider wrapper — thin delegation to agent-wallet's BaseProvider interface.

The provider only provides address query and signing.
Chain reads (balance, allowance, contract calls) are handled by the signers
themselves via ``create_async_tron_client``.

Interface::

    get_address() -> str
    sign_tx(unsigned_tx) -> {"signed_tx": Any, "signature": str | None}
    sign_message(message: bytes) -> str
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseProviderWrapper(ABC):
    """Abstract wrapper mirroring agent-wallet's BaseProvider interface.

    The provider only handles:
    - **Address**: ``get_address()``
    - **Signing**: ``sign_tx()``, ``sign_message()``

    All chain reads (balance, allowance, contract calls, tx receipts) are
    performed by the signers via a separate ``AsyncTron`` client.
    """

    @abstractmethod
    async def get_address(self) -> str:
        """Get the wallet address.

        Returns:
            TRON address string (e.g. ``T...``).
        """
        ...

    @abstractmethod
    async def sign_tx(self, unsigned_tx: Any) -> dict[str, Any]:
        """Sign an unsigned transaction and return the signed result.

        Returns:
            Dict with ``{"signed_tx": Any, "signature": str | None}``.
        """
        ...

    @abstractmethod
    async def sign_message(self, message: bytes) -> str:
        """Sign a raw message (e.g. EIP-191 personal_sign hash).

        Returns:
            Hex-encoded signature string.
        """
        ...


class TronProviderWrapper(BaseProviderWrapper):
    """Wrapper for agent-wallet's ``TronProvider``.

    Usage::

        provider = await TronProvider.create(private_key="deadbeef...")
        wrapper = await TronProviderWrapper.create(provider)
    """

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    @classmethod
    async def create(cls, provider: Any) -> "TronProviderWrapper":
        wrapper = cls(provider=provider)
        await wrapper.get_address()
        return wrapper

    async def get_address(self) -> str:
        info = await self._provider.get_account_info()
        address = info.get("address")
        if not address:
            raise ValueError("Provider returned no address from get_account_info()")
        return address

    async def sign_tx(self, unsigned_tx: Any) -> dict[str, Any]:
        return await self._provider.sign_tx(unsigned_tx)

    async def sign_message(self, message: bytes) -> str:
        return await self._provider.sign_message(message)
