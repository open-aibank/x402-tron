"""
KeyProvider Protocol - abstraction for provider address access.

Any provider backend (agent-wallet, HSM, remote signer, etc.)
can be used with x402 signers by implementing this protocol.

Note: Private keys are never exposed through this protocol.
All signing is delegated to the provider via ``BaseProviderWrapper``.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class KeyProvider(Protocol):
    """Minimal interface that a provider backend must satisfy.

    agent-wallet's TronProvider can be adapted via
    ``TronProviderAdapter``.
    """

    def get_address(self) -> str:
        """Return the TRON base58check address."""
        ...
