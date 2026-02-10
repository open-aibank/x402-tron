"""
NativeExactTronServerMechanism - native_exact server mechanism for TRON.
"""

from x402_tron.mechanisms.native_exact.base import NativeExactBaseServerMechanism
from x402_tron.mechanisms.native_exact.tron.adapter import TronChainAdapter


class NativeExactTronServerMechanism(NativeExactBaseServerMechanism):
    """TransferWithAuthorization server mechanism for TRON."""

    def __init__(self) -> None:
        super().__init__(TronChainAdapter())
