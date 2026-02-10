"""
NativeExactEvmClientMechanism - native_exact client mechanism for EVM.
"""

from typing import TYPE_CHECKING

from x402_tron.mechanisms._native_exact_base.base import NativeExactBaseClientMechanism
from x402_tron.mechanisms.evm.native_exact.adapter import EvmChainAdapter

if TYPE_CHECKING:
    from x402_tron.signers.client import ClientSigner


class NativeExactEvmClientMechanism(NativeExactBaseClientMechanism):
    """TransferWithAuthorization client mechanism for EVM."""

    def __init__(self, signer: "ClientSigner") -> None:
        super().__init__(signer, EvmChainAdapter())
