"""
x402 - Payment Protocol SDK for Python

Supports Client, Server, and Facilitator functionality for multi-chain payments.
"""

__version__ = "0.1.0"

from tvm_x402.types import (
    PaymentPermit,
    PaymentPayload,
    PaymentRequirements,
    PaymentRequired,
    VerifyResponse,
    SettleResponse,
)
from tvm_x402.exceptions import (
    X402Error,
    SignatureError,
    SignatureVerificationError,
    AllowanceError,
    SettlementError,
    TransactionError,
    TransactionTimeoutError,
    ValidationError,
    PermitValidationError,
    ConfigurationError,
    UnsupportedNetworkError,
    UnknownTokenError,
)
from tvm_x402.address import (
    AddressConverter,
    EvmAddressConverter,
    TronAddressConverter,
)
from tvm_x402.tokens import TokenInfo, TokenRegistry

__all__ = [
    "__version__",
    # Types
    "PaymentPermit",
    "PaymentPayload",
    "PaymentRequirements",
    "PaymentRequired",
    "VerifyResponse",
    "SettleResponse",
    # Exceptions
    "X402Error",
    "SignatureError",
    "SignatureVerificationError",
    "AllowanceError",
    "SettlementError",
    "TransactionError",
    "TransactionTimeoutError",
    "ValidationError",
    "PermitValidationError",
    "ConfigurationError",
    "UnsupportedNetworkError",
    "UnknownTokenError",
    # Address converters
    "AddressConverter",
    "EvmAddressConverter",
    "TronAddressConverter",
    # Token registry
    "TokenInfo",
    "TokenRegistry",
]
