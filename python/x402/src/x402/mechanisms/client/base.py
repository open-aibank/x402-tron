"""
客户端机制基础接口
"""

from abc import ABC, abstractmethod
from typing import Any

from x402.types import PaymentPayload, PaymentRequirements


class ClientMechanism(ABC):
    """
    客户端支付机制的抽象基类

    负责为特定链/方案创建支付载荷
    """

    @abstractmethod
    def scheme(self) -> str:
        """获取支付方案名称"""
        pass

    @abstractmethod
    async def create_payment_payload(
        self,
        requirements: PaymentRequirements,
        resource: str,
        extensions: dict[str, Any] | None = None,
    ) -> PaymentPayload:
        """
        为给定的要求创建支付载荷

        Args:
            requirements: 来自服务器的支付要求
            resource: 资源 URL
            extensions: 可选扩展（例如 paymentPermitContext）

        Returns:
            包含签名的 PaymentPayload
        """
        pass
