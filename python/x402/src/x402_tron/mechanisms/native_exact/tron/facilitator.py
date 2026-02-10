"""
NativeExactTronFacilitatorMechanism - native_exact facilitator mechanism for TRON.
"""

from typing import TYPE_CHECKING

from x402_tron.mechanisms.native_exact.base import NativeExactBaseFacilitatorMechanism
from x402_tron.mechanisms.native_exact.tron.adapter import TronChainAdapter

if TYPE_CHECKING:
    from x402_tron.signers.facilitator import FacilitatorSigner


class NativeExactTronFacilitatorMechanism(NativeExactBaseFacilitatorMechanism):
    """TransferWithAuthorization facilitator mechanism for TRON."""

    def __init__(
        self,
        signer: "FacilitatorSigner",
        allowed_tokens: set[str] | None = None,
    ) -> None:
        super().__init__(signer, TronChainAdapter(), allowed_tokens)
