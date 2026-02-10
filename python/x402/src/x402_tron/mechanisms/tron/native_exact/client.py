"""
NativeExactTronClientMechanism - native_exact client mechanism for TRON.
"""

from typing import TYPE_CHECKING

from x402_tron.mechanisms._native_exact_base.base import NativeExactBaseClientMechanism
from x402_tron.mechanisms.tron.native_exact.adapter import TronChainAdapter

if TYPE_CHECKING:
    from x402_tron.signers.client import ClientSigner


class NativeExactTronClientMechanism(NativeExactBaseClientMechanism):
    """TransferWithAuthorization client mechanism for TRON."""

    def __init__(self, signer: "ClientSigner") -> None:
        super().__init__(signer, TronChainAdapter())
