"""
TronChainMixin - Shared chain-read and allowance logic for TRON client signers.

Provides:
- AsyncTron client management
- TRC20 balance / allowance queries
- ensure_allowance orchestration (delegates signing to subclass hook)
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any

from x402_tron.abi import ERC20_ABI
from x402_tron.config import NetworkConfig
from x402_tron.exceptions import InsufficientAllowanceError

logger = logging.getLogger(__name__)


class TronChainMixin:
    """Mixin providing shared TRON chain-read and allowance logic.

    Subclasses must:
    - Set ``self._address: str`` and ``self._network: str | None``
    - Initialise ``self._async_tron_clients: dict[str, Any] = {}``
    - Implement ``_sign_and_broadcast_approval``
    """

    _address: str
    _network: str | None
    _async_tron_clients: dict[str, Any]

    # ------------------------------------------------------------------
    # AsyncTron client management
    # ------------------------------------------------------------------

    def _ensure_async_tron_client(self, network: str | None = None) -> Any:
        """Lazy initialize async tron_client for the given network.

        Args:
            network: Network identifier. Falls back to self._network if None.

        Returns:
            tronpy.AsyncTron instance or None
        """
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

    # ------------------------------------------------------------------
    # Chain reads
    # ------------------------------------------------------------------

    async def check_balance(
        self,
        token: str,
        network: str,
    ) -> int:
        """Check TRC20 token balance"""
        client = self._ensure_async_tron_client(network)
        if not client:
            logger.warning("AsyncTron client not available, returning 0 balance")
            return 0

        try:
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
        """Check token allowance on TRON"""
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

        client = self._ensure_async_tron_client(network)
        if not client:
            logger.warning("AsyncTron client not available, returning 0 allowance")
            return 0

        try:
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

    # ------------------------------------------------------------------
    # Allowance orchestration
    # ------------------------------------------------------------------

    async def ensure_allowance(
        self,
        token: str,
        amount: int,
        network: str,
        mode: str = "auto",
    ) -> bool:
        """Ensure sufficient allowance"""
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
        client = self._ensure_async_tron_client(network)
        if not client:
            raise InsufficientAllowanceError("AsyncTron client required for approval")

        try:
            spender = self._get_spender_address(network)
            # Use maxUint160 (2^160 - 1) to avoid repeated approvals
            max_uint160 = (2**160) - 1
            logger.info(f"Approving spender={spender} for amount={max_uint160} (maxUint160)")
            contract = await client.get_contract(token)
            contract.abi = ERC20_ABI
            txn_builder = await contract.functions.approve(spender, max_uint160)
            txn_builder = txn_builder.with_owner(self._address).fee_limit(100_000_000)
            txn = await txn_builder.build()

            # Delegate signing + broadcast to subclass
            return await self._sign_and_broadcast_approval(txn)
        except InsufficientAllowanceError:
            raise
        except Exception as e:
            raise InsufficientAllowanceError(f"Approval transaction failed: {e}") from e

    @abstractmethod
    async def _sign_and_broadcast_approval(self, txn: Any) -> bool:
        """Sign and broadcast an approval transaction.

        Args:
            txn: Built (unsigned) tronpy transaction.

        Returns:
            True if the approval succeeded.
        """
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_spender_address(self, network: str) -> str:
        """Get payment permit contract address (spender)"""
        return NetworkConfig.get_payment_permit_address(network)
