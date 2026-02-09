"""MyProvider — tronpy-based provider that implements the BaseProvider interface.

Does NOT depend on the ``wallet`` package. Uses tronpy's ``PrivateKey`` directly
for signing transactions and messages.

Interface (same as agent-wallet's BaseProvider)::

    get_account_info() -> {"address": str}
    sign_tx(unsigned_tx) -> {"signed_tx": Any, "signature": str | None}
    sign_message(message: bytes) -> str

Usage::

    from x402_tron.signers.my_provider import MyProvider

    provider = MyProvider(private_key="your_hex_key")
    wrapper = await TronProviderWrapper.create(provider)
"""

from __future__ import annotations

from typing import Any

from tronpy.keys import PrivateKey


class MyProvider:
    """Minimal tronpy-based provider — no ``wallet`` dependency required."""

    def __init__(self, private_key: str) -> None:
        pk_hex = private_key[2:] if private_key.startswith("0x") else private_key
        self._pk_bytes = bytes.fromhex(pk_hex)
        self._key = PrivateKey(self._pk_bytes)
        self.address = self._key.public_key.to_base58check_address()

    async def get_account_info(self) -> dict[str, str]:
        """Get account info (wallet address)."""
        return {"address": self.address}

    async def sign_tx(self, unsigned_tx: Any) -> dict[str, Any]:
        """Sign an unsigned tronpy transaction."""
        signed = unsigned_tx.sign(self._key)
        sig = getattr(signed, "_signature", None) or getattr(signed, "signature", None)
        if isinstance(sig, list) and len(sig) > 0:
            raw_sig = sig[0]
            signature = raw_sig if isinstance(raw_sig, str) else None
        else:
            signature = None
        return {"signed_tx": signed, "signature": signature}

    async def sign_message(self, message: bytes) -> str:
        """Sign a 32-byte hash with raw ECDSA (Ethereum-compatible recoverable signature).

        Returns a 65-byte hex signature (r + s + v) where v is 27 or 28,
        compatible with Solidity's ``ecrecover``.
        """
        from coincurve import PrivateKey as CPrivateKey

        pk = CPrivateKey(self._pk_bytes)
        raw_sig = pk.sign_recoverable(message, hasher=None)
        # raw_sig: r(32) + s(32) + v(1) where v is 0 or 1
        r = raw_sig[:32]
        s = raw_sig[32:64]
        v = raw_sig[64] + 27  # Ethereum convention: 27/28
        return (r + s + bytes([v])).hex()
