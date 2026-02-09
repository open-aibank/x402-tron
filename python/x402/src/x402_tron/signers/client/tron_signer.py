"""
TronClientSigner - TRON client signer implementation
"""

import json
import logging
from typing import Any

from x402_tron.abi import EIP712_DOMAIN_TYPE, PAYMENT_PERMIT_PRIMARY_TYPE
from x402_tron.exceptions import SignatureCreationError
from x402_tron.signers.client.base import ClientSigner
from x402_tron.signers.client.tron_chain_mixin import TronChainMixin

logger = logging.getLogger(__name__)


class TronClientSigner(TronChainMixin, ClientSigner):
    """TRON client signer implementation"""

    def __init__(self, private_key: str, network: str | None = None) -> None:
        clean_key = private_key[2:] if private_key.startswith("0x") else private_key
        self._private_key = clean_key
        self._address = self._derive_address(clean_key)
        self._network = network
        self._async_tron_clients: dict[str, Any] = {}
        logger.info(f"TronClientSigner initialized: address={self._address}, network={network}")

    @classmethod
    def from_private_key(cls, private_key: str, network: str | None = None) -> "TronClientSigner":
        """Create signer from private key.

        Args:
            private_key: TRON private key (hex string)
            network: Optional TRON network (mainnet/shasta/nile) for lazy client initialization

        Returns:
            TronClientSigner instance
        """
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

    async def sign_message(self, message: bytes) -> str:
        """Sign raw message using ECDSA"""
        try:
            from tronpy.keys import PrivateKey

            pk = PrivateKey(bytes.fromhex(self._private_key))
            signature = pk.sign_msg(message)
            return signature.hex()
        except ImportError:
            raise SignatureCreationError("tronpy is required for signing")

    async def sign_typed_data(
        self,
        domain: dict[str, Any],
        types: dict[str, Any],
        message: dict[str, Any],
    ) -> str:
        """Sign EIP-712 typed data.

        Note: The primaryType is determined from the types dict.
        For PaymentPermit contract, it should be "PaymentPermitDetails".
        """
        # Determine primary type from types dict (should be the last/main type)
        # For PaymentPermit, the main type is "PaymentPermitDetails"
        primary_type = (
            PAYMENT_PERMIT_PRIMARY_TYPE
            if PAYMENT_PERMIT_PRIMARY_TYPE in types
            else list(types.keys())[-1]
        )
        logger.info(
            f"Signing EIP-712 typed data: domain={domain.get('name')}, primaryType={primary_type}"
        )
        try:
            from eth_account import Account
            from eth_account.messages import encode_typed_data

            # Note: PaymentPermit contract uses EIP712Domain WITHOUT version field
            # Contract:
            # keccak256("EIP712Domain(string name,uint256 chainId,address verifyingContract)")
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

            # Log domain and message in same format as TypeScript client
            import json as json_module

            # Convert bytes to hex for logging
            message_for_log = dict(message)
            if "meta" in message_for_log and "paymentId" in message_for_log["meta"]:
                pid = message_for_log["meta"]["paymentId"]
                if isinstance(pid, bytes):
                    message_for_log["meta"] = dict(message_for_log["meta"])
                    message_for_log["meta"]["paymentId"] = "0x" + pid.hex()

            logger.info(f"[SIGN] Domain: {json_module.dumps(domain)}")
            logger.info(f"[SIGN] Message: {json_module.dumps(message_for_log)}")

            signable = encode_typed_data(full_message=typed_data)
            # Convert hex private key to bytes for eth_account
            private_key_bytes = bytes.fromhex(self._private_key)
            signed_message = Account.sign_message(signable, private_key_bytes)

            signature = signed_message.signature.hex()
            logger.info(f"[SIGN] Signature: 0x{signature}")
            return signature
        except ImportError:
            logger.warning("eth_account not available, using fallback signing")
            data_str = json.dumps({"domain": domain, "types": types, "message": message})
            return await self.sign_message(data_str.encode())

    async def _sign_and_broadcast_approval(self, txn: Any) -> bool:
        """Sign approval tx with local private key and broadcast."""
        from tronpy.keys import PrivateKey

        txn = txn.sign(PrivateKey(bytes.fromhex(self._private_key)))
        logger.info("Broadcasting approval transaction...")
        result = await txn.broadcast()
        result = await result.wait()
        # Check receipt.result for success (TRON returns "SUCCESS" in receipt)
        receipt = result.get("receipt", {})
        receipt_result = receipt.get("result", "")
        success = receipt_result == "SUCCESS"
        if success:
            logger.info(f"Approval successful: txid={result.get('id')}")
        else:
            logger.warning(f"Approval failed: {result}")
        return success
