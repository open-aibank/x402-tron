"""
X402 Network Configuration
Centralized configuration for contract addresses and network settings
"""

import os
from typing import Dict


class NetworkConfig:
    """Network configuration for contract addresses and chain IDs"""

    # Default networks (CAIP-2 format)
    TRON_MAINNET = "tron:728126428"   # 0x2b6653dc
    TRON_SHASTA = "tron:2494104990"   # 0x94a9059e
    TRON_NILE = "tron:3448148188"     # 0xcd8690dc

    # TRON Chain IDs
    CHAIN_IDS: Dict[str, int] = {
        "tron:728126428": 728126428,   # mainnet
        "tron:2494104990": 2494104990,   # shasta
        "tron:3448148188": 3448148188,     # nile
    }

    # PaymentPermit contract addresses
    PAYMENT_PERMIT_ADDRESSES: Dict[str, str] = {
        "tron:728126428": "T...",  # TODO: Deploy and fill (mainnet)
        "tron:2494104990": "T...",  # TODO: Deploy and fill (shasta)
        "tron:3448148188": "TCR6EaRtLRYjWPr7YWHqt4uL81rfevtE8p",  # nile
    }

    @classmethod
    def get_chain_id(cls, network: str) -> int:
        """Get chain ID for network
        
        Args:
            network: Network identifier (e.g., "tron:3448148188", "tron:728126428")
            
        Returns:
            Chain ID as integer
            
        Raises:
            ValueError: If network is not supported
        """
        chain_id = cls.CHAIN_IDS.get(network)
        if chain_id is None:
            raise ValueError(f"Unsupported network: {network}")
        return chain_id

    @classmethod
    def get_payment_permit_address(cls, network: str) -> str:
        """Get PaymentPermit contract address for network
        
        Args:
            network: Network identifier (e.g., "tron:3448148188", "tron:728126428")
            
        Returns:
            Contract address in Base58 format
        """
        return cls.PAYMENT_PERMIT_ADDRESSES.get(
            network, "T0000000000000000000000000000000"
        )
