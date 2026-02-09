"""
AgentWalletFacilitatorSigner - Facilitator signer backed by agent-wallet provider.

Signing is delegated to the provider wrapper; chain reads use a local
``AsyncTron`` client (shared via ``TronFacilitatorChainMixin``).
"""

from __future__ import annotations

import logging
from typing import Any

from x402_tron.signers.facilitator.base import FacilitatorSigner
from x402_tron.signers.facilitator.tron_chain_mixin import TronFacilitatorChainMixin
from x402_tron.signers.provider_wrapper import BaseProviderWrapper, TronProviderWrapper

logger = logging.getLogger(__name__)


class AgentWalletFacilitatorSigner(TronFacilitatorChainMixin, FacilitatorSigner):
    """Facilitator signer that takes an agent-wallet provider directly.

    - **Signing** (sign_tx) → delegated to provider wrapper.
    - **Chain reads** (contract calls, tx receipts) → local ``AsyncTron`` client.
    - Private keys are never accessed by this class.

    Usage::

        from wallet import TronProvider
        from x402_tron.signers.facilitator import AgentWalletFacilitatorSigner

        provider = await TronProvider.create(private_key="deadbeef...")
        signer = await AgentWalletFacilitatorSigner.create(provider, network="tron:nile")
    """

    def __init__(self, wrapper: BaseProviderWrapper, network: str | None = None) -> None:
        self._wrapper = wrapper
        self._address: str | None = None  # resolved in create()
        self._network = network
        self._async_tron_clients: dict[str, Any] = {}

    @classmethod
    async def create(
        cls,
        provider: Any,
        network: str | None = None,
        *,
        wrapper: BaseProviderWrapper | None = None,
    ) -> "AgentWalletFacilitatorSigner":
        """Async factory — creates the wrapper and resolves address from provider."""
        if wrapper is None:
            wrapper = await TronProviderWrapper.create(provider)
        instance = cls(wrapper=wrapper, network=network)
        instance._address = await wrapper.get_address()
        logger.info("AgentWalletFacilitatorSigner initialized: address=%s", instance._address)
        return instance

    def get_address(self) -> str:
        return self._address

    async def _sign_transaction(self, txn: Any) -> Any:
        """Sign transaction via provider wrapper (no private key access)."""
        result = await self._wrapper.sign_tx(txn)
        return result["signed_tx"]
