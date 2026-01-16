"""
UptoTronFacilitatorMechanism - "upto" 支付方案的 TRON facilitator 机制
"""

import json
import logging
import time
from typing import Any, TYPE_CHECKING

from x402.abi import PAYMENT_PERMIT_ABI, MERCHANT_ABI, get_abi_json, get_payment_permit_eip712_types
from x402.config import NetworkConfig
from x402.mechanisms.facilitator.base import FacilitatorMechanism
from x402.types import (
    PaymentPayload,
    PaymentRequirements,
    VerifyResponse,
    SettleResponse,
    FeeQuoteResponse,
    FeeInfo,
    KIND_MAP,
    PAYMENT_AND_DELIVERY,
)
from x402.utils import normalize_tron_address, tron_address_to_evm

if TYPE_CHECKING:
    from x402.signers.facilitator import FacilitatorSigner

logger = logging.getLogger(__name__)


class UptoTronFacilitatorMechanism(FacilitatorMechanism):
    """"upto" 支付方案的 TRON facilitator 机制"""

    def __init__(
        self,
        signer: "FacilitatorSigner",
        fee_to: str | None = None,
        base_fee: int = 1000000,
    ) -> None:
        self._signer = signer
        self._fee_to = fee_to or signer.get_address()
        self._base_fee = base_fee
        logger.info(f"UptoTronFacilitatorMechanism initialized: fee_to={self._fee_to}, base_fee={base_fee}")

    def scheme(self) -> str:
        return "exact"

    async def fee_quote(
        self,
        accept: PaymentRequirements,
        context: dict[str, Any] | None = None,
    ) -> FeeQuoteResponse:
        """基于 gas 估算计算费用报价"""
        fee_amount = str(self._base_fee)
        logger.info(f"Fee quote requested: network={accept.network}, amount={accept.amount}, fee={fee_amount}")

        return FeeQuoteResponse(
            fee=FeeInfo(
                feeTo=self._fee_to,
                feeAmount=fee_amount,
            ),
            pricing="per_accept",
            network=accept.network,
            expiresAt=int(time.time()) + 300,
        )

    async def verify(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
    ) -> VerifyResponse:
        """验证支付签名"""
        permit = payload.payload.payment_permit
        signature = payload.payload.signature
        logger.info(f"Verifying payment: paymentId={permit.meta.payment_id}, buyer={permit.buyer}, amount={permit.payment.max_pay_amount}")

        if int(permit.payment.max_pay_amount) < int(requirements.amount):
            logger.warning(f"Amount mismatch: {permit.payment.max_pay_amount} < {requirements.amount}")
            return VerifyResponse(isValid=False, invalidReason="amount_mismatch")

        if permit.payment.pay_to != requirements.pay_to:
            logger.warning(f"PayTo mismatch: {permit.payment.pay_to} != {requirements.pay_to}")
            return VerifyResponse(isValid=False, invalidReason="payto_mismatch")

        if permit.payment.pay_token != requirements.asset:
            logger.warning(f"Token mismatch: {permit.payment.pay_token} != {requirements.asset}")
            return VerifyResponse(isValid=False, invalidReason="token_mismatch")

        now = int(time.time())
        if permit.meta.valid_before < now:
            logger.warning(f"Permit expired: validBefore={permit.meta.valid_before} < now={now}")
            return VerifyResponse(isValid=False, invalidReason="expired")

        if permit.meta.valid_after > now:
            logger.warning(f"Permit not yet valid: validAfter={permit.meta.valid_after} > now={now}")
            return VerifyResponse(isValid=False, invalidReason="not_yet_valid")

        logger.info("Verifying EIP-712 signature...")
        # Convert permit to dict and replace kind string with numeric value for EIP-712
        message = permit.model_dump(by_alias=True)
        kind_num = KIND_MAP.get(permit.meta.kind, 0)
        message["meta"]["kind"] = kind_num
        
        # Convert TRON addresses to EVM format for EIP-712 compatibility
        message["buyer"] = tron_address_to_evm(message["buyer"])
        message["caller"] = tron_address_to_evm(message["caller"])
        message["payment"]["payToken"] = tron_address_to_evm(message["payment"]["payToken"])
        message["payment"]["payTo"] = tron_address_to_evm(message["payment"]["payTo"])
        message["fee"]["feeTo"] = tron_address_to_evm(message["fee"]["feeTo"])
        message["delivery"]["receiveToken"] = tron_address_to_evm(message["delivery"]["receiveToken"])
        
        # Get payment permit contract address and chain ID for domain
        from x402.config import NetworkConfig
        permit_address = self._get_payment_permit_address(requirements.network)
        permit_address_evm = tron_address_to_evm(permit_address)
        chain_id = NetworkConfig.get_chain_id(requirements.network)
        
        # Note: Contract EIP712Domain only has (name, chainId, verifyingContract) - NO version!
        is_valid = await self._signer.verify_typed_data(
            address=permit.buyer,
            domain={
                "name": "PaymentPermit",
                "chainId": chain_id,
                "verifyingContract": permit_address_evm,
            },
            types=get_payment_permit_eip712_types(),
            message=message,
            signature=signature,
        )

        if not is_valid:
            logger.warning("Invalid signature")
            return VerifyResponse(isValid=False, invalidReason="invalid_signature")

        logger.info("Payment verification successful")
        return VerifyResponse(isValid=True)

    async def settle(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
    ) -> SettleResponse:
        """Execute payment settlement on TRON"""
        permit = payload.payload.payment_permit
        logger.info(f"Starting settlement: paymentId={permit.meta.payment_id}, kind={permit.meta.kind}, network={requirements.network}")
        logger.info(f"Permit validBefore from payload: {permit.meta.valid_before}, validAfter: {permit.meta.valid_after}")
        
        verify_result = await self.verify(payload, requirements)
        if not verify_result.is_valid:
            logger.error(f"Settlement failed: verification failed - {verify_result.invalid_reason}")
            return SettleResponse(
                success=False,
                errorReason=verify_result.invalid_reason,
                network=requirements.network,
            )

        signature = payload.payload.signature

        kind = permit.meta.kind
        if kind == PAYMENT_AND_DELIVERY:
            logger.info("Settling with delivery via merchant contract...")
            tx_hash = await self._settle_with_delivery(permit, signature, requirements)
        else:
            logger.info("Settling payment only via PaymentPermit contract...")
            tx_hash = await self._settle_payment_only(permit, signature, requirements)

        if tx_hash is None:
            logger.error("Settlement transaction failed: no transaction hash returned")
            return SettleResponse(
                success=False,
                errorReason="transaction_failed",
                network=requirements.network,
            )

        logger.info(f"Transaction broadcast successful: txHash={tx_hash}")
        logger.info("Waiting for transaction receipt...")
        receipt = await self._signer.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Transaction confirmed: {receipt}")

        return SettleResponse(
            success=True,
            transaction=tx_hash,
            network=requirements.network,
        )

    async def _settle_payment_only(
        self,
        permit: Any,
        signature: str,
        requirements: PaymentRequirements,
    ) -> str | None:
        """Settle payment only (no on-chain delivery)"""
        contract_address = self._get_payment_permit_address(requirements.network)
        logger.info(f"Calling permitTransferFrom on contract={contract_address}")
        
        # Convert permit to tuple format for contract call
        # Convert paymentId to bytes if it's a hex string
        payment_id = permit.meta.payment_id
        if isinstance(payment_id, str):
            payment_id = bytes.fromhex(payment_id[2:] if payment_id.startswith("0x") else payment_id)
        
        # Normalize addresses to ensure valid Base58Check format
        buyer = normalize_tron_address(permit.buyer)
        caller = normalize_tron_address(permit.caller)
        pay_token = normalize_tron_address(permit.payment.pay_token)
        pay_to = normalize_tron_address(permit.payment.pay_to)
        fee_to = normalize_tron_address(permit.fee.fee_to)
        receive_token = normalize_tron_address(permit.delivery.receive_token)
        
        logger.info(f"Settlement addresses: buyer={buyer}, caller={caller}, pay_token={pay_token}, pay_to={pay_to}, fee_to={fee_to}, receive_token={receive_token}")
        logger.info(f"Settlement amounts: max_pay={permit.payment.max_pay_amount}, fee={permit.fee.fee_amount}")
        logger.info(f"Settlement meta: kind={permit.meta.kind}, paymentId={permit.meta.payment_id}, nonce={permit.meta.nonce}")
        logger.info(f"Settlement time: validAfter={permit.meta.valid_after}, validBefore={permit.meta.valid_before}, current_time={int(time.time())}")
        
        # Build PaymentPermit tuple for contract call
        # Contract struct: (PermitMeta meta, address buyer, address caller, Payment payment, Fee fee, Delivery delivery)
        permit_tuple = (
            (  # meta tuple
                KIND_MAP.get(permit.meta.kind, 0),
                payment_id,
                int(permit.meta.nonce),
                permit.meta.valid_after,
                permit.meta.valid_before,
            ),
            buyer,  # buyer address
            caller,  # caller address
            (  # payment tuple
                pay_token,
                int(permit.payment.max_pay_amount),
                pay_to,
            ),
            (  # fee tuple
                fee_to,
                int(permit.fee.fee_amount),
            ),
            (  # delivery tuple
                receive_token,
                int(permit.delivery.mini_receive_amount),
                int(permit.delivery.token_id),
            ),
        )
        
        # Convert signature hex string to bytes
        sig_bytes = bytes.fromhex(signature[2:] if signature.startswith("0x") else signature)
        
        # Build transferDetails tuple: (amount)
        # Note: TransferDetails only contains amount, not to address
        # The to address is taken from permit.payment.payTo
        transfer_details = (
            int(permit.payment.max_pay_amount),
        )
        
        args = [
            permit_tuple,
            transfer_details,
            buyer,
            sig_bytes,
        ]
        
        logger.info(f"Calling permitTransferFrom with {len(args)} arguments (PAYMENT_ONLY mode)")
        logger.info(f"  transferDetails: amount={permit.payment.max_pay_amount}")
        
        return await self._signer.write_contract(
            contract_address=self._get_payment_permit_address(requirements.network),
            abi=self._get_payment_permit_abi(),
            method="permitTransferFrom",
            args=args,
        )

    async def _settle_with_delivery(
        self,
        permit: Any,
        signature: str,
        requirements: PaymentRequirements,
    ) -> str | None:
        """Settle with on-chain delivery via merchant contract"""
        merchant_address = self._get_merchant_address(requirements)
        logger.info(f"Calling settle on merchant contract={merchant_address}")
        logger.info(f"[_settle_with_delivery] Original paymentId from permit: {permit.meta.payment_id}")
        
        # Convert paymentId to bytes if it's a hex string
        payment_id = permit.meta.payment_id
        if isinstance(payment_id, str):
            payment_id = bytes.fromhex(payment_id[2:] if payment_id.startswith("0x") else payment_id)
        
        logger.info(f"[_settle_with_delivery] Converted paymentId (bytes hex): 0x{payment_id.hex()}")
        
        # Normalize addresses to ensure valid Base58Check format
        # Note: tronpy requires TRON format addresses (T...), not EVM format (0x...)
        buyer = normalize_tron_address(permit.buyer)
        caller = normalize_tron_address(permit.caller)
        pay_token = normalize_tron_address(permit.payment.pay_token)
        pay_to = normalize_tron_address(permit.payment.pay_to)
        fee_to = normalize_tron_address(permit.fee.fee_to)
        receive_token = normalize_tron_address(permit.delivery.receive_token)
        
        logger.info(f"[_settle_with_delivery] buyer={buyer}, caller={caller}")
        logger.info(f"[_settle_with_delivery] pay_token={pay_token}, pay_to={pay_to}")
        logger.info(f"[_settle_with_delivery] fee_to={fee_to}, receive_token={receive_token}")
        logger.info(f"[_settle_with_delivery] meta: kind={permit.meta.kind}, nonce={permit.meta.nonce}")
        logger.info(f"[_settle_with_delivery] time: validAfter={permit.meta.valid_after}, validBefore={permit.meta.valid_before}, current_time={int(time.time())}")
        logger.info(f"[_settle_with_delivery] delivery: miniReceiveAmount={permit.delivery.mini_receive_amount}, tokenId={permit.delivery.token_id}")
        
        # Build PaymentPermit tuple for contract call
        permit_tuple = (
            (  # meta tuple
                KIND_MAP.get(permit.meta.kind, 0),
                payment_id,
                int(permit.meta.nonce),
                permit.meta.valid_after,
                permit.meta.valid_before,
            ),
            buyer,
            caller,
            (  # payment tuple
                pay_token,
                int(permit.payment.max_pay_amount),
                pay_to,
            ),
            (  # fee tuple
                fee_to,
                int(permit.fee.fee_amount),
            ),
            (  # delivery tuple
                receive_token,
                int(permit.delivery.mini_receive_amount),
                int(permit.delivery.token_id),
            ),
        )
        
        # Convert signature hex string to bytes
        sig_bytes = bytes.fromhex(signature[2:] if signature.startswith("0x") else signature)
        
        return await self._signer.write_contract(
            contract_address=merchant_address,
            abi=self._get_merchant_abi(),
            method="settle",
            args=[permit_tuple, sig_bytes],
        )

    def _get_payment_permit_address(self, network: str) -> str:
        """Get payment permit contract address for network"""
        return NetworkConfig.get_payment_permit_address(network)

    def _get_merchant_address(self, requirements: PaymentRequirements) -> str:
        """Get merchant contract address"""
        return requirements.pay_to

    def _get_payment_permit_abi(self) -> str:
        """Get payment permit contract ABI"""
        return get_abi_json(PAYMENT_PERMIT_ABI)

    def _get_merchant_abi(self) -> str:
        """Get merchant contract ABI"""
        return get_abi_json(MERCHANT_ABI)


