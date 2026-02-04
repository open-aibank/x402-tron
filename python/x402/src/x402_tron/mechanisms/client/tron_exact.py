"""
ExactTronClientMechanism - "exact" 支付方案的 TRON 客户端机制
"""

from x402_tron.address import AddressConverter, TronAddressConverter
from x402_tron.mechanisms.client.base_exact import BaseExactClientMechanism


class ExactTronClientMechanism(BaseExactClientMechanism):
    def _get_address_converter(self) -> AddressConverter:
        return TronAddressConverter()
