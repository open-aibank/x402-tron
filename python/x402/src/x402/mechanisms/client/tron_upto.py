"""
UptoTronClientMechanism - "upto" 支付方案的 TRON 客户端机制
"""

from typing import Any, TYPE_CHECKING

from x402.mechanisms.client.base import ClientMechanism
from x402.types import (
    PaymentPayload,
    PaymentPayloadData,
    PaymentPermit,
    PaymentRequirements,
    PermitMeta,
    Payment,
    Fee,
    Delivery,
    ResourceInfo,
)

if TYPE_CHECKING:
    from x402.signers.client import ClientSigner


class UptoTronClientMechanism(ClientMechanism):
    """"upto" 支付方案的 TRON 客户端机制"""

    def __init__(self, signer: "ClientSigner") -> None:
        self._signer = signer

    def scheme(self) -> str:
        return "exact"

    async def create_payment_payload(
        self,
        requirements: PaymentRequirements,
        resource: str,
        extensions: dict[str, Any] | None = None,
    ) -> PaymentPayload:
        """使用 EIP-712 签名创建支付载荷"""
        context = extensions.get("paymentPermitContext") if extensions else None
        if context is None:
            raise ValueError("paymentPermitContext is required")

        buyer_address = self._signer.get_address()
        meta = context.get("meta", {})
        delivery = context.get("delivery", {})

        fee_to = "410000000000000000000000000000000000000000"
        fee_amount = "0"
        if requirements.extra and requirements.extra.fee:
            fee_to = requirements.extra.fee.fee_to
            fee_amount = requirements.extra.fee.fee_amount

        permit = PaymentPermit(
            meta=PermitMeta(
                kind=meta.get("kind", "PAYMENT_ONLY"),
                paymentId=meta.get("paymentId", ""),
                nonce=str(meta.get("nonce", "0")),
                validAfter=meta.get("validAfter", 0),
                validBefore=meta.get("validBefore", 0),
            ),
            buyer=buyer_address,
            caller=fee_to,
            payment=Payment(
                payToken=requirements.asset,
                maxPayAmount=requirements.amount,
                payTo=requirements.pay_to,
            ),
            fee=Fee(
                feeTo=fee_to,
                feeAmount=fee_amount,
            ),
            delivery=Delivery(
                receiveToken=delivery.get("receiveToken", "T0000000000000000000000000000000"),
                miniReceiveAmount=str(delivery.get("miniReceiveAmount", "0")),
                tokenId=str(delivery.get("tokenId", "0")),
            ),
        )

        total_amount = int(permit.payment.max_pay_amount) + int(permit.fee.fee_amount)
        await self._signer.ensure_allowance(
            permit.payment.pay_token,
            total_amount,
            requirements.network,
        )

        signature = await self._signer.sign_typed_data(
            domain={"name": "PaymentPermit", "version": "1"},
            types=self._get_eip712_types(),
            message=permit.model_dump(by_alias=True),
        )

        return PaymentPayload(
            x402Version=2,
            resource=ResourceInfo(url=resource),
            accepted=requirements,
            payload=PaymentPayloadData(
                signature=signature,
                paymentPermit=permit,
            ),
            extensions={},
        )

    def _get_eip712_types(self) -> dict[str, Any]:
        """Get EIP-712 type definitions"""
        return {
            "PermitMeta": [
                {"name": "kind", "type": "uint8"},
                {"name": "paymentId", "type": "bytes16"},
                {"name": "nonce", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
            ],
            "Payment": [
                {"name": "payToken", "type": "address"},
                {"name": "maxPayAmount", "type": "uint256"},
                {"name": "payTo", "type": "address"},
            ],
            "Fee": [
                {"name": "feeTo", "type": "address"},
                {"name": "feeAmount", "type": "uint256"},
            ],
            "Delivery": [
                {"name": "receiveToken", "type": "address"},
                {"name": "miniReceiveAmount", "type": "uint256"},
                {"name": "tokenId", "type": "uint256"},
            ],
            "PaymentPermit": [
                {"name": "meta", "type": "PermitMeta"},
                {"name": "buyer", "type": "address"},
                {"name": "caller", "type": "address"},
                {"name": "payment", "type": "Payment"},
                {"name": "fee", "type": "Fee"},
                {"name": "delivery", "type": "Delivery"},
            ],
        }
