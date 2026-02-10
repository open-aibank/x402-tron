"""
NativeExactEvmServerMechanism - native_exact server mechanism for EVM.
"""

from x402_tron.mechanisms.native_exact.base import NativeExactBaseServerMechanism
from x402_tron.mechanisms.native_exact.evm.adapter import EvmChainAdapter


class NativeExactEvmServerMechanism(NativeExactBaseServerMechanism):
    """TransferWithAuthorization server mechanism for EVM."""

    def __init__(self) -> None:
        super().__init__(EvmChainAdapter())
