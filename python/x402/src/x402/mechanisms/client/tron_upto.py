"""
UptoTronClientMechanism - "upto" 支付方案的 TRON 客户端机制
"""

import logging
from typing import Any, TYPE_CHECKING

from x402.abi import get_payment_permit_eip712_types
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
    KIND_MAP,
    PAYMENT_ONLY,
)
from x402.utils import normalize_tron_address, tron_address_to_evm

if TYPE_CHECKING:
    from x402.signers.client import ClientSigner

logger = logging.getLogger(__name__)


class UptoTronClientMechanism(ClientMechanism):
    """"upto" 支付方案的 TRON 客户端机制"""

    def __init__(self, signer: "ClientSigner") -> None:
        self._signer = signer
        logger.info("UptoTronClientMechanism initialized")

    def scheme(self) -> str:
        return "exact"

    async def create_payment_payload(
        self,
        requirements: PaymentRequirements,
        resource: str,
        extensions: dict[str, Any] | None = None,
    ) -> PaymentPayload:
        """使用 EIP-712 签名创建支付载荷"""
        logger.info(f"Creating payment payload: network={requirements.network}, amount={requirements.amount}, asset={requirements.asset}")
        context = extensions.get("paymentPermitContext") if extensions else None
        if context is None:
            raise ValueError("paymentPermitContext is required")

        buyer_address = self._signer.get_address()
        meta = context.get("meta", {})
        delivery = context.get("delivery", {})
        logger.debug(f"Buyer address: {buyer_address}, paymentId: {meta.get('paymentId')}")

        # Use zero address in TRON format as default
        fee_to = "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"
        fee_amount = "0"
        if requirements.extra and requirements.extra.fee:
            fee_to = requirements.extra.fee.fee_to
            fee_amount = requirements.extra.fee.fee_amount

        kind_str = meta.get("kind", PAYMENT_ONLY)
        kind_num = KIND_MAP.get(kind_str, 0)
        
        # Get caller from context, default to zero address if not provided
        caller = context.get("caller", "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb")  # Zero address in TRON format
        
        permit = PaymentPermit(
            meta=PermitMeta(
                kind=kind_str,
                paymentId=meta.get("paymentId", ""),
                nonce=str(meta.get("nonce", "0")),
                validAfter=meta.get("validAfter", 0),
                validBefore=meta.get("validBefore", 0),
            ),
            buyer=buyer_address,
            caller=caller,
            payment=Payment(
                payToken=normalize_tron_address(requirements.asset),
                maxPayAmount=requirements.amount,
                payTo=normalize_tron_address(requirements.pay_to),
            ),
            fee=Fee(
                feeTo=fee_to,
                feeAmount=fee_amount,
            ),
            delivery=Delivery(
                receiveToken=normalize_tron_address(delivery.get("receiveToken", "T0000000000000000000000000000000")),
                miniReceiveAmount=str(delivery.get("miniReceiveAmount", "0")),
                tokenId=str(delivery.get("tokenId", "0")),
            ),
        )

        total_amount = int(permit.payment.max_pay_amount) + int(permit.fee.fee_amount)
        logger.info(f"Total amount (payment + fee): {total_amount} = {permit.payment.max_pay_amount} + {permit.fee.fee_amount}")
        
        await self._signer.ensure_allowance(
            permit.payment.pay_token,
            total_amount,
            requirements.network,
        )

        logger.info("Signing payment permit with EIP-712...")
        # Convert permit to dict and replace kind string with numeric value for EIP-712
        message = permit.model_dump(by_alias=True)
        message["meta"]["kind"] = kind_num
        
        # Convert string values to integers for EIP-712 compatibility
        # EIP-712 expects uint256 types to be integers, not strings
        message["meta"]["nonce"] = int(message["meta"]["nonce"])
        message["payment"]["maxPayAmount"] = int(message["payment"]["maxPayAmount"])
        message["fee"]["feeAmount"] = int(message["fee"]["feeAmount"])
        message["delivery"]["miniReceiveAmount"] = int(message["delivery"]["miniReceiveAmount"])
        message["delivery"]["tokenId"] = int(message["delivery"]["tokenId"])
        
        # Convert TRON addresses to EVM format for EIP-712 compatibility
        message["buyer"] = tron_address_to_evm(message["buyer"])
        message["caller"] = tron_address_to_evm(message["caller"])
        message["payment"]["payToken"] = tron_address_to_evm(message["payment"]["payToken"])
        message["payment"]["payTo"] = tron_address_to_evm(message["payment"]["payTo"])
        message["fee"]["feeTo"] = tron_address_to_evm(message["fee"]["feeTo"])
        message["delivery"]["receiveToken"] = tron_address_to_evm(message["delivery"]["receiveToken"])
        
        # Get payment permit contract address and chain ID for domain
        from x402.config import NetworkConfig
        permit_address = NetworkConfig.get_payment_permit_address(requirements.network)
        permit_address_evm = tron_address_to_evm(permit_address)
        chain_id = NetworkConfig.get_chain_id(requirements.network)
        
        # Note: Contract EIP712Domain only has (name, chainId, verifyingContract) - NO version!
        signature = await self._signer.sign_typed_data(
            domain={
                "name": "PaymentPermit",
                "chainId": chain_id,
                "verifyingContract": permit_address_evm,
            },
            types=get_payment_permit_eip712_types(),
            message=message,
        )

        logger.info(f"Payment payload created successfully: signature={signature[:10]}...")
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
