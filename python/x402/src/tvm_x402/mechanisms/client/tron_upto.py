"""
UptoTronClientMechanism - "upto" 支付方案的 TRON 客户端机制
"""

from tvm_x402.address import AddressConverter, TronAddressConverter
from tvm_x402.mechanisms.client.base_upto import BaseUptoClientMechanism


class UptoTronClientMechanism(BaseUptoClientMechanism):
    """upto 支付方案的 TRON 客户端机制"""

    def _get_address_converter(self) -> AddressConverter:
        return TronAddressConverter()
