"""
NativeExactTronServerMechanism - native_exact server mechanism for TRON.
"""

from x402_tron.mechanisms._native_exact_base.base import NativeExactBaseServerMechanism
from x402_tron.mechanisms.tron.native_exact.adapter import TronChainAdapter


class NativeExactTronServerMechanism(NativeExactBaseServerMechanism):
    """TransferWithAuthorization server mechanism for TRON."""

    def __init__(self) -> None:
        super().__init__(TronChainAdapter())
