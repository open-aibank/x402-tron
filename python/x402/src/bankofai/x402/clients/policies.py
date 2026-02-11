"""
Payment policies for filtering or reordering payment requirements.

Policies are applied in order after mechanism filtering and before token selection.
"""

import logging
from typing import TYPE_CHECKING

from bankofai.x402.tokens import TokenRegistry
from bankofai.x402.types import PaymentRequirements

if TYPE_CHECKING:
    from bankofai.x402.signers.client.base import ClientSigner

logger = logging.getLogger(__name__)


def _get_decimals(req: PaymentRequirements) -> int:
    """Look up token decimals from the registry, default to 6."""
    token = TokenRegistry.find_by_address(req.network, req.asset)
    return token.decimals if token else 6


def _match_pattern(pattern: str, network: str) -> bool:
    """Match a network against a pattern (e.g. 'tron:*' matches 'tron:nile')."""
    if pattern == network:
        return True
    if pattern.endswith(":*"):
        return network.startswith(pattern[:-1])
    return False


class SufficientBalancePolicy:
    """Policy that filters out requirements with insufficient balance.

    When the server accepts multiple tokens (e.g. USDT and USDD),
    this policy checks the user's on-chain balance for each option
    and removes requirements the user cannot afford.

    Supports multi-network setups: pass a single signer for single-network
    use, or a dict[networkPattern, signer] for multi-network.

    Requirements whose network has no matching signer are kept as-is
    (not filtered out), so downstream mechanism matching can still work.

    If all requirements are unaffordable, returns an empty list so the
    caller can raise an appropriate error.
    """

    def __init__(
        self,
        signers: "ClientSigner | dict[str, ClientSigner]",
    ) -> None:
        if isinstance(signers, dict):
            self._signers: list[tuple[str, "ClientSigner"]] = list(signers.items())
        else:
            self._signers = [("*", signers)]

    def _find_signer(self, network: str) -> "ClientSigner | None":
        for pattern, signer in self._signers:
            if pattern == "*" or _match_pattern(pattern, network):
                return signer
        return None

    async def apply(
        self,
        requirements: list[PaymentRequirements],
    ) -> list[PaymentRequirements]:
        affordable: list[PaymentRequirements] = []
        for req in requirements:
            signer = self._find_signer(req.network)
            if signer is None:
                # No signer for this network — keep the requirement so
                # mechanism matching can still select it.
                affordable.append(req)
                continue

            try:
                balance = await signer.check_balance(req.asset, req.network)
            except Exception:
                # Signer cannot query this network; keep the requirement.
                affordable.append(req)
                continue

            needed = int(req.amount)
            if hasattr(req, "extra") and req.extra and hasattr(req.extra, "fee"):
                fee = req.extra.fee
                if fee and hasattr(fee, "fee_amount"):
                    needed += int(fee.fee_amount)
            decimals = _get_decimals(req)
            token_info = TokenRegistry.find_by_address(req.network, req.asset)
            symbol = token_info.symbol if token_info else req.asset[:8]
            divisor = 10**decimals
            h_balance = balance / divisor
            h_needed = needed / divisor
            fmt = f"%.{decimals}f"
            if balance >= needed:
                logger.info(
                    f"%s on %s: balance={fmt} >= needed={fmt} (OK)",
                    symbol,
                    req.network,
                    h_balance,
                    h_needed,
                )
                affordable.append(req)
            else:
                logger.info(
                    f"%s on %s: balance={fmt} < needed={fmt} (skipped)",
                    symbol,
                    req.network,
                    h_balance,
                    h_needed,
                )
        if not affordable:
            logger.error("All payment requirements filtered: insufficient balance")
        return affordable
