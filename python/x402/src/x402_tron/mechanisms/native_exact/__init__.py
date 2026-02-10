"""
native_exact mechanism - TransferWithAuthorization for EVM and TRON.

Uses transferWithAuthorization directly on the token contract
instead of the PaymentPermit contract.
"""

from x402_tron.mechanisms.native_exact.base import (
    ChainAdapter,
    NativeExactBaseClientMechanism,
    NativeExactBaseFacilitatorMechanism,
    NativeExactBaseServerMechanism,
)
from x402_tron.mechanisms.native_exact.evm import (
    NativeExactEvmClientMechanism,
    NativeExactEvmFacilitatorMechanism,
    NativeExactEvmServerMechanism,
)
from x402_tron.mechanisms.native_exact.tron import (
    NativeExactTronClientMechanism,
    NativeExactTronFacilitatorMechanism,
    NativeExactTronServerMechanism,
)

__all__ = [
    # Base
    "ChainAdapter",
    "NativeExactBaseClientMechanism",
    "NativeExactBaseFacilitatorMechanism",
    "NativeExactBaseServerMechanism",
    # EVM
    "NativeExactEvmClientMechanism",
    "NativeExactEvmFacilitatorMechanism",
    "NativeExactEvmServerMechanism",
    # TRON
    "NativeExactTronClientMechanism",
    "NativeExactTronFacilitatorMechanism",
    "NativeExactTronServerMechanism",
]
