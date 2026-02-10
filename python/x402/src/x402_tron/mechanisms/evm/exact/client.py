"""
ExactEvmClientMechanism - "exact" payment scheme EVM client mechanism
"""

from x402_tron.address import AddressConverter, EvmAddressConverter
from x402_tron.mechanisms._exact_base.client import BaseExactClientMechanism


class ExactEvmClientMechanism(BaseExactClientMechanism):
    def _get_address_converter(self) -> AddressConverter:
        return EvmAddressConverter()
