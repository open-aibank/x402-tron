"""
x402 Mechanisms - Payment mechanisms for different chains

Structure:
    _base/               - ABC interfaces (ClientMechanism, FacilitatorMechanism, ServerMechanism)
    _exact_base/         - Shared base classes for "exact" scheme
    _native_exact_base/  - Shared base classes for "native_exact" scheme
    evm/                 - EVM chain implementations
        exact/           - exact scheme (client, facilitator, server)
        native_exact/    - native_exact scheme (adapter, client, facilitator, server)
    tron/                - TRON chain implementations
        exact/           - exact scheme (client, facilitator, server)
        native_exact/    - native_exact scheme (adapter, client, facilitator, server)
"""

from x402_tron.mechanisms import evm, tron
from x402_tron.mechanisms._base import ClientMechanism, FacilitatorMechanism, ServerMechanism
from x402_tron.mechanisms._exact_base import (
    BaseExactClientMechanism,
    BaseExactFacilitatorMechanism,
    BaseExactServerMechanism,
)
from x402_tron.mechanisms._native_exact_base import (
    ChainAdapter,
    NativeExactBaseClientMechanism,
    NativeExactBaseFacilitatorMechanism,
    NativeExactBaseServerMechanism,
)
from x402_tron.mechanisms.evm import (
    ExactEvmClientMechanism,
    ExactEvmFacilitatorMechanism,
    ExactEvmServerMechanism,
    NativeExactEvmClientMechanism,
    NativeExactEvmFacilitatorMechanism,
    NativeExactEvmServerMechanism,
)
from x402_tron.mechanisms.tron import (
    ExactTronClientMechanism,
    ExactTronFacilitatorMechanism,
    ExactTronServerMechanism,
    NativeExactTronClientMechanism,
    NativeExactTronFacilitatorMechanism,
    NativeExactTronServerMechanism,
)

__all__ = [
    # Base interfaces
    "ClientMechanism",
    "FacilitatorMechanism",
    "ServerMechanism",
    # Exact base
    "BaseExactClientMechanism",
    "BaseExactFacilitatorMechanism",
    "BaseExactServerMechanism",
    # Native exact base
    "ChainAdapter",
    "NativeExactBaseClientMechanism",
    "NativeExactBaseFacilitatorMechanism",
    "NativeExactBaseServerMechanism",
    # EVM
    "ExactEvmClientMechanism",
    "ExactEvmFacilitatorMechanism",
    "ExactEvmServerMechanism",
    "NativeExactEvmClientMechanism",
    "NativeExactEvmFacilitatorMechanism",
    "NativeExactEvmServerMechanism",
    # TRON
    "ExactTronClientMechanism",
    "ExactTronFacilitatorMechanism",
    "ExactTronServerMechanism",
    "NativeExactTronClientMechanism",
    "NativeExactTronFacilitatorMechanism",
    "NativeExactTronServerMechanism",
    # Subpackages
    "evm",
    "tron",
]
