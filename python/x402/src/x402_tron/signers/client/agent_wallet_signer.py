"""
AgentWalletClientSigner - Client signer backed by agent-wallet provider.

Standalone implementation that directly inherits from ``ClientSigner``.
Signing is delegated to the provider wrapper; chain reads use a local
``AsyncTron`` client (same pattern as ``TronClientSigner``).
"""

from __future__ import annotations

import logging
from typing import Any

from x402_tron.abi import ERC20_ABI, PAYMENT_PERMIT_PRIMARY_TYPE
from x402_tron.config import NetworkConfig
from x402_tron.exceptions import InsufficientAllowanceError
from x402_tron.signers.client.base import ClientSigner
from x402_tron.signers.provider_wrapper import BaseProviderWrapper, TronProviderWrapper

logger = logging.getLogger(__name__)


class AgentWalletClientSigner(ClientSigner):
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

    def _ensure_async_tron_client(self, network: str | None = None) -> Any:
        """Lazy initialize AsyncTron client for chain reads."""
        net = network or self._network
        if not net:
            return None
        if net not in self._async_tron_clients:
            try:
                from x402_tron.utils.tron_client import create_async_tron_client

                self._async_tron_clients[net] = create_async_tron_client(net)
            except ImportError:
                return None
        return self._async_tron_clients[net]

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

    async def check_balance(
        self,
        token: str,
        network: str,
    ) -> int:
        """Check TRC20 token balance via local AsyncTron client."""
        try:
            client = self._ensure_async_tron_client(network)
            if not client:
                logger.error(f"No AsyncTron client for network {network}")
                return 0
            contract = await client.get_contract(token)
            contract.abi = ERC20_ABI
            balance = await contract.functions.balanceOf(self._address)
            balance_int = int(balance)

            from x402_tron.tokens import TokenRegistry

            token_info = TokenRegistry.find_by_address(network, token)
            decimals = token_info.decimals if token_info else 6
            symbol = token_info.symbol if token_info else token[:8]
            human = balance_int / (10**decimals)
            logger.info(
                f"Token balance: {human:.6f} {symbol} "
                f"(raw={balance_int}, token={token}, network={network})"
            )
            return balance_int
        except Exception as e:
            logger.error(f"Failed to check balance: {e}")
            return 0

    async def check_allowance(
        self,
        token: str,
        amount: int,
        network: str,
    ) -> int:
        """Check token allowance via local AsyncTron client."""
        spender = self._get_spender_address(network)
        logger.info(
            "Checking allowance: token=%s, owner=%s, spender=%s, network=%s",
            token,
            self._address,
            spender,
            network,
        )
        if not spender or spender == "T0000000000000000000000000000000":
            logger.warning(
                f"Invalid spender address for network {network}, skipping allowance check"
            )
            return 0

        try:
            client = self._ensure_async_tron_client(network)
            if not client:
                logger.error(f"No AsyncTron client for network {network}")
                return 0
            contract = await client.get_contract(token)
            contract.abi = ERC20_ABI
            allowance = await contract.functions.allowance(
                self._address,
                spender,
            )
            allowance_int = int(allowance)
            logger.info(f"Current allowance: {allowance_int}")
            return allowance_int
        except Exception as e:
            logger.error(f"Failed to check allowance: {e}")
            return 0

    async def ensure_allowance(
        self,
        token: str,
        amount: int,
        network: str,
        mode: str = "auto",
    ) -> bool:
        """Ensure sufficient allowance — builds tx locally, signs via wrapper."""
        logger.info(
            f"Ensuring allowance: token={token}, amount={amount}, network={network}, mode={mode}"
        )
        if mode == "skip":
            logger.info("Skipping allowance check (mode=skip)")
            return True

        current = await self.check_allowance(token, amount, network)
        if current >= amount:
            logger.info(f"Sufficient allowance already exists: {current} >= {amount}")
            return True

        if mode == "interactive":
            raise NotImplementedError("Interactive approval not implemented")

        logger.info(f"Insufficient allowance ({current} < {amount}), requesting approval...")

        try:
            client = self._ensure_async_tron_client(network)
            if not client:
                raise InsufficientAllowanceError(f"No AsyncTron client for network {network}")
            spender = self._get_spender_address(network)
            max_uint160 = (2**160) - 1
            logger.info(f"Approving spender={spender} for amount={max_uint160} (maxUint160)")
            contract = await client.get_contract(token)
            contract.abi = ERC20_ABI
            txn_builder = await contract.functions.approve(spender, max_uint160)
            txn_builder = txn_builder.with_owner(self._address).fee_limit(100_000_000)
            txn = await txn_builder.build()
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
        except InsufficientAllowanceError:
            raise
        except Exception as e:
            raise InsufficientAllowanceError(f"Approval transaction failed: {e}") from e

    def _get_spender_address(self, network: str) -> str:
        """Get payment permit contract address (spender)"""
        return NetworkConfig.get_payment_permit_address(network)
