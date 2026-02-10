"""
ExactEvmClientMechanism - "exact" payment scheme EVM client mechanism
"""

from x402_tron.address import AddressConverter, EvmAddressConverter
from x402_tron.mechanisms.client.base_exact import BaseExactClientMechanism


class ExactEvmClientMechanism(BaseExactClientMechanism):
    def _get_address_converter(self) -> AddressConverter:
        return EvmAddressConverter()
