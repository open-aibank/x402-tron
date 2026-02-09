"""
Adapter that bridges agent-wallet providers to a read-only address interface.

Never accesses private keys — all signing is delegated to the provider via
``BaseProviderWrapper``.
"""

from __future__ import annotations

from typing import Any


class TronProviderAdapter:
    """Adapt agent-wallet's ``TronProvider`` (or ``FlashProvider``) to a
    minimal read-only interface.

    Only reads ``address`` via the provider's ``get_account_info()`` method.
    Private keys are **never** extracted — signing is handled by the
    provider wrapper.

    Use the async ``create()`` factory to construct::

        adapter = await TronProviderAdapter.create(provider)
    """

    def __init__(self, address: str, provider: Any) -> None:
        self._provider = provider
        self._address = address

    @classmethod
    async def create(cls, provider: Any) -> "TronProviderAdapter":
        """Create adapter by calling provider.get_account_info()."""
        info = await provider.get_account_info()
        address = info.get("address")
        if not address:
            raise ValueError("Provider returned no address from get_account_info()")
        return cls(address=address, provider=provider)

    def get_address(self) -> str:
        return self._address
