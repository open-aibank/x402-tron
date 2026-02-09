"""
AgentWalletClientSigner - Client signer backed by agent-wallet provider.

Signing is delegated to the provider wrapper; chain reads use a local
``AsyncTron`` client (shared via ``TronChainMixin``).
"""

from __future__ import annotations

import logging
from typing import Any

from x402_tron.abi import PAYMENT_PERMIT_PRIMARY_TYPE
from x402_tron.signers.client.base import ClientSigner
from x402_tron.signers.client.tron_chain_mixin import TronChainMixin
from x402_tron.signers.provider_wrapper import BaseProviderWrapper, TronProviderWrapper

logger = logging.getLogger(__name__)


class AgentWalletClientSigner(TronChainMixin, ClientSigner):
    """Client signer that takes an agent-wallet provider directly.

    - **Signing** (sign_typed_data, sign_tx) → delegated to provider wrapper.
    - **Chain reads** (balance, allowance, approve) → local ``AsyncTron`` client.
    - Private keys are never accessed by this class.

    Usage::

        from wallet import TronProvider
        from x402_tron.signers.client import AgentWalletClientSigner

        provider = await TronProvider.create(private_key="deadbeef...")
        signer = await AgentWalletClientSigner.create(provider, network="tron:nile")
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
    ) -> "AgentWalletClientSigner":
        """Async factory — creates the wrapper and resolves address from provider."""
        if wrapper is None:
            wrapper = await TronProviderWrapper.create(provider)
        instance = cls(wrapper=wrapper, network=network)
        instance._address = await wrapper.get_address()
        logger.info("AgentWalletClientSigner initialized: address=%s", instance._address)
        return instance

    def get_address(self) -> str:
        return self._address

    async def sign_message(self, message: bytes) -> str:
        """Sign raw message — delegates to provider wrapper."""
        return await self._wrapper.sign_message(message)

    async def sign_typed_data(
        self,
        domain: dict[str, Any],
        types: dict[str, Any],
        message: dict[str, Any],
    ) -> str:
        """Sign EIP-712 typed data.

        Encodes the typed data locally, then delegates the raw signing
        to the provider via ``wrapper.sign_message()``.
        """
        from eth_account.messages import encode_typed_data

        from x402_tron.abi import EIP712_DOMAIN_TYPE

        primary_type = (
            PAYMENT_PERMIT_PRIMARY_TYPE
            if PAYMENT_PERMIT_PRIMARY_TYPE in types
            else list(types.keys())[-1]
        )
        logger.info(
            f"Signing EIP-712 typed data: domain={domain.get('name')}, primaryType={primary_type}"
        )

        full_types = {
            "EIP712Domain": EIP712_DOMAIN_TYPE,
            **types,
        }
        typed_data = {
            "types": full_types,
            "primaryType": primary_type,
            "domain": domain,
            "message": message,
        }
        signable = encode_typed_data(full_message=typed_data)
        # Compute the full EIP-712 hash: keccak256(\x19\x01 + domainSeparator + messageHash)
        from eth_utils import keccak

        eip712_hash = keccak(b"\x19" + signable.version + signable.header + signable.body)
        signature = await self._wrapper.sign_message(eip712_hash)
        logger.info(f"[SIGN] Signature: 0x{signature}")
        return signature

    async def _sign_and_broadcast_approval(self, txn: Any) -> bool:
        """Sign approval tx via provider wrapper and broadcast."""
        # Sign via provider wrapper (no private key access)
        result = await self._wrapper.sign_tx(txn)
        signed_txn = result["signed_tx"]
        logger.info("Broadcasting approval transaction...")
        broadcast_result = await signed_txn.broadcast()
        broadcast_result = await broadcast_result.wait()
        receipt = broadcast_result.get("receipt", {})
        receipt_result = receipt.get("result", "")
        success = receipt_result == "SUCCESS"
        if success:
            logger.info(f"Approval successful: txid={broadcast_result.get('id')}")
        else:
            logger.warning(f"Approval failed: {broadcast_result}")
        return success
