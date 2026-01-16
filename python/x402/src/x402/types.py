"""
x402 协议的类型定义
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# Delivery Kind constants
PAYMENT_ONLY = "PAYMENT_ONLY"
PAYMENT_AND_DELIVERY = "PAYMENT_AND_DELIVERY"

DeliveryKind = Literal["PAYMENT_ONLY", "PAYMENT_AND_DELIVERY"]

# Kind mapping for EIP-712 (string to numeric)
KIND_MAP = {
    PAYMENT_ONLY: 0,
    PAYMENT_AND_DELIVERY: 1,
}


class PermitMeta(BaseModel):
    """支付许可元数据"""
    kind: DeliveryKind
    payment_id: str = Field(alias="paymentId")
    nonce: str
    valid_after: int = Field(alias="validAfter")
    valid_before: int = Field(alias="validBefore")

    class Config:
        populate_by_name = True


class Payment(BaseModel):
    """支付信息"""
    pay_token: str = Field(alias="payToken")
    max_pay_amount: str = Field(alias="maxPayAmount")
    pay_to: str = Field(alias="payTo")

    class Config:
        populate_by_name = True


class Fee(BaseModel):
    """费用信息"""
    fee_to: str = Field(alias="feeTo")
    fee_amount: str = Field(alias="feeAmount")

    class Config:
        populate_by_name = True


class Delivery(BaseModel):
    """链上交付的交付信息"""
    receive_token: str = Field(alias="receiveToken")
    mini_receive_amount: str = Field(alias="miniReceiveAmount")
    token_id: str = Field(alias="tokenId")

    class Config:
        populate_by_name = True


class PaymentPermit(BaseModel):
    """支付许可结构"""
    meta: PermitMeta
    buyer: str
    caller: str
    payment: Payment
    fee: Fee
    delivery: Delivery


class FeeInfo(BaseModel):
    """支付要求中的费用信息"""
    facilitator_id: Optional[str] = Field(None, alias="facilitatorId")
    fee_to: str = Field(alias="feeTo")
    fee_amount: str = Field(alias="feeAmount")

    class Config:
        populate_by_name = True


class PaymentRequirementsExtra(BaseModel):
    """支付要求中的额外信息"""
    name: Optional[str] = None
    version: Optional[str] = None
    fee: Optional[FeeInfo] = None


class PaymentRequirements(BaseModel):
    """来自服务器的支付要求"""
    scheme: str
    network: str
    amount: str
    asset: str
    pay_to: str = Field(alias="payTo")
    max_timeout_seconds: Optional[int] = Field(None, alias="maxTimeoutSeconds")
    extra: Optional[PaymentRequirementsExtra] = None

    class Config:
        populate_by_name = True


class PaymentPermitContextMeta(BaseModel):
    """支付许可上下文中的元信息"""
    kind: DeliveryKind
    payment_id: str = Field(alias="paymentId")
    nonce: str
    valid_after: int = Field(alias="validAfter")
    valid_before: int = Field(alias="validBefore")

    class Config:
        populate_by_name = True


class PaymentPermitContextDelivery(BaseModel):
    """支付许可上下文中的交付信息"""
    receive_token: str = Field(alias="receiveToken")
    mini_receive_amount: str = Field(alias="miniReceiveAmount")
    token_id: str = Field(alias="tokenId")

    class Config:
        populate_by_name = True


class PaymentPermitContext(BaseModel):
    """来自扩展的支付许可上下文"""
    meta: PaymentPermitContextMeta
    caller: Optional[str] = None  # 可选的 caller 地址，零地址表示允许任何地址调用
    delivery: PaymentPermitContextDelivery


class ResourceInfo(BaseModel):
    """资源信息"""
    url: Optional[str] = None
    description: Optional[str] = None
    mime_type: Optional[str] = Field(None, alias="mimeType")

    class Config:
        populate_by_name = True


class PaymentRequiredExtensions(BaseModel):
    """PaymentRequired 中的扩展"""
    payment_permit_context: Optional[PaymentPermitContext] = Field(
        None, alias="paymentPermitContext"
    )

    class Config:
        populate_by_name = True
        extra = "allow"


class PaymentRequired(BaseModel):
    """需要支付响应 (402)"""
    x402_version: int = Field(alias="x402Version")
    error: Optional[str] = None
    resource: Optional[ResourceInfo] = None
    accepts: list[PaymentRequirements]
    extensions: Optional[PaymentRequiredExtensions] = None

    class Config:
        populate_by_name = True


class PaymentPayloadData(BaseModel):
    """支付载荷数据"""
    signature: str
    merchant_signature: Optional[str] = Field(None, alias="merchantSignature")
    payment_permit: PaymentPermit = Field(alias="paymentPermit")

    class Config:
        populate_by_name = True


class PaymentPayload(BaseModel):
    """客户端发送的支付载荷"""
    x402_version: int = Field(alias="x402Version")
    resource: Optional[ResourceInfo] = None
    accepted: PaymentRequirements
    payload: PaymentPayloadData
    extensions: Optional[dict[str, Any]] = None

    class Config:
        populate_by_name = True


class VerifyResponse(BaseModel):
    """来自中间层的验证响应"""
    is_valid: bool = Field(alias="isValid")
    invalid_reason: Optional[str] = Field(None, alias="invalidReason")

    class Config:
        populate_by_name = True


class TransactionInfo(BaseModel):
    """交易信息"""
    hash: str
    block_number: Optional[str] = Field(None, alias="blockNumber")
    status: Optional[str] = None


class SettleResponse(BaseModel):
    """来自中间层的结算响应"""
    success: bool
    transaction: Optional[str] = None
    network: Optional[str] = None
    error_reason: Optional[str] = Field(None, alias="errorReason")

    class Config:
        populate_by_name = True


class SupportedKind(BaseModel):
    """支持的支付类型"""
    x402_version: int = Field(alias="x402Version")
    scheme: str
    network: str

    class Config:
        populate_by_name = True


class SupportedFee(BaseModel):
    """支持的费用配置"""
    fee_to: str = Field(alias="feeTo")
    pricing: Literal["per_accept", "flat"]

    class Config:
        populate_by_name = True


class SupportedResponse(BaseModel):
    """来自中间层的支持响应"""
    kinds: list[SupportedKind]
    fee: Optional[SupportedFee] = None


class FeeQuoteResponse(BaseModel):
    """来自中间层的费用报价响应"""
    fee: FeeInfo
    pricing: str
    network: str
    expires_at: Optional[int] = Field(None, alias="expiresAt")

    class Config:
        populate_by_name = True
