"""
Pytest 配置和测试夹具
"""

import pytest


@pytest.fixture
def mock_tron_private_key():
    """用于测试的模拟 TRON 私钥"""
    return "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


@pytest.fixture
def mock_evm_private_key():
    """用于测试的模拟 EVM 私钥"""
    return "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


@pytest.fixture
def mock_tron_payment_requirements():
    """用于测试的模拟 TRON 支付要求"""
    from x402.types import PaymentRequirements
    from x402.config import NetworkConfig

    return PaymentRequirements(
        scheme="exact",
        network=NetworkConfig.TRON_SHASTA,
        amount="1000000",
        asset="TTestUSDTAddress",
        payTo="TTestMerchantAddress",
        maxTimeoutSeconds=3600,
    )


@pytest.fixture
def mock_evm_payment_requirements():
    """用于测试的模拟 EVM 支付要求"""
    from x402.types import PaymentRequirements

    return PaymentRequirements(
        scheme="exact",
        network="eip155:8453",
        amount="1000000",
        asset="0xTestUSDCAddress",
        payTo="0xTestMerchantAddress",
        maxTimeoutSeconds=3600,
    )
