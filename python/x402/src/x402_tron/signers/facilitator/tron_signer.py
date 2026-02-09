"""
TronFacilitatorSigner - TRON facilitator signer implementation
"""

import logging
from typing import Any

from x402_tron.signers.facilitator.base import FacilitatorSigner
from x402_tron.signers.facilitator.tron_chain_mixin import TronFacilitatorChainMixin

logger = logging.getLogger(__name__)


class TronFacilitatorSigner(TronFacilitatorChainMixin, FacilitatorSigner):
    """TRON facilitator signer implementation"""

    def __init__(self, private_key: str, network: str | None = None) -> None:
        clean_key = private_key[2:] if private_key.startswith("0x") else private_key
        self._private_key = clean_key
        self._address = self._derive_address(clean_key)
        self._network = network
        self._async_tron_clients: dict[str, Any] = {}

    @classmethod
    def from_private_key(
        cls, private_key: str, network: str | None = None
    ) -> "TronFacilitatorSigner":
        """Create signer from private key"""
        return cls(private_key, network)

    @staticmethod
    def _derive_address(private_key: str) -> str:
        """Derive TRON address from private key"""
        try:
            from tronpy.keys import PrivateKey

            pk = PrivateKey(bytes.fromhex(private_key))
            return pk.public_key.to_base58check_address()
        except ImportError:
            return f"T{private_key[:33]}"

    def get_address(self) -> str:
        return self._address

    def _evm_to_tron_address(self, evm_address: str) -> str:
        """Convert EVM address to TRON address"""
        try:
            from tronpy.keys import to_base58check_address

            hex_addr = "41" + evm_address[2:].lower()
            return to_base58check_address(hex_addr)
        except ImportError:
            return evm_address

    async def _sign_transaction(self, txn: Any) -> Any:
        """Sign transaction with local private key."""
        from tronpy.keys import PrivateKey

        return txn.sign(PrivateKey(bytes.fromhex(self._private_key)))
