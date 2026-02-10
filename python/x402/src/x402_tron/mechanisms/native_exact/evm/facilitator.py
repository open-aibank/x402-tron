"""
NativeExactEvmFacilitatorMechanism - native_exact facilitator mechanism for EVM.
"""

from typing import TYPE_CHECKING

from x402_tron.mechanisms.native_exact.base import NativeExactBaseFacilitatorMechanism
from x402_tron.mechanisms.native_exact.evm.adapter import EvmChainAdapter

if TYPE_CHECKING:
    from x402_tron.signers.facilitator import FacilitatorSigner


class NativeExactEvmFacilitatorMechanism(NativeExactBaseFacilitatorMechanism):
    """TransferWithAuthorization facilitator mechanism for EVM."""

    def __init__(
        self,
        signer: "FacilitatorSigner",
        allowed_tokens: set[str] | None = None,
    ) -> None:
        super().__init__(signer, EvmChainAdapter(), allowed_tokens)
