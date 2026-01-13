"""
UptoTronServerMechanism - "upto" 支付方案的 TRON 服务器机制
"""

from typing import Any

from x402.mechanisms.server.base import ServerMechanism
from x402.types import PaymentRequirements, PaymentRequirementsExtra


TRON_KNOWN_TOKENS: dict[str, dict[str, Any]] = {
    "tron:mainnet": {
        "USDT": {
            "address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            "decimals": 6,
            "name": "Tether USD",
            "version": "1",
        },
        "TRX": {
            "address": "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb",
            "decimals": 6,
            "name": "TRON",
            "version": "1",
        },
    },
    "tron:shasta": {
        "USDT": {
            "address": "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs",
            "decimals": 6,
            "name": "Tether USD",
            "version": "1",
        },
    },
    "tron:nile": {
        "USDT": {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "decimals": 6,
            "name": "Tether USD",
            "version": "1",
        },
    },
}


class UptoTronServerMechanism(ServerMechanism):
    """"upto" 支付方案的 TRON 服务器机制"""

    def scheme(self) -> str:
        """返回支付方案"""
        return "exact"

    async def parse_price(self, price: str, network: str) -> dict[str, Any]:
        """将价格字符串解析为资产金额

        Args:
            price: 价格字符串（例如 "100 USDT"）
            network: 网络标识符（例如 "tron:mainnet"）

        Returns:
            包含 amount、asset、decimals 的字典
        """
        parts = price.strip().split()
        if len(parts) != 2:
            raise ValueError(f"Invalid price format: {price}")

        amount_str, symbol = parts
        amount = float(amount_str)

        tokens = TRON_KNOWN_TOKENS.get(network, {})
        token_info = tokens.get(symbol.upper())

        if token_info is None:
            raise ValueError(f"Unknown token {symbol} on network {network}")

        decimals = token_info["decimals"]
        amount_smallest = int(amount * (10 ** decimals))

        return {
            "amount": amount_smallest,
            "asset": token_info["address"],
            "decimals": decimals,
            "symbol": symbol.upper(),
            "name": token_info["name"],
            "version": token_info["version"],
        }

    async def enhance_payment_requirements(
        self,
        requirements: PaymentRequirements,
        kind: str,
    ) -> PaymentRequirements:
        """Enhance payment requirements with token metadata"""
        if requirements.extra is None:
            requirements.extra = PaymentRequirementsExtra()

        tokens = TRON_KNOWN_TOKENS.get(requirements.network, {})
        for symbol, info in tokens.items():
            if info["address"] == requirements.asset:
                requirements.extra.name = info["name"]
                requirements.extra.version = info["version"]
                break

        return requirements

    def validate_payment_requirements(self, requirements: PaymentRequirements) -> bool:
        """Validate TRON payment requirements"""
        if not requirements.network.startswith("tron:"):
            return False

        if not requirements.asset.startswith("T"):
            return False

        if not requirements.pay_to.startswith("T"):
            return False

        try:
            amount = int(requirements.amount)
            if amount <= 0:
                return False
        except ValueError:
            return False

        return True
