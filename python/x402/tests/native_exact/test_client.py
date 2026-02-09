"""
Tests for NativeExactTronClientMechanism.
"""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from x402_tron.mechanisms.native_exact.client import NativeExactTronClientMechanism
from x402_tron.mechanisms.native_exact.types import SCHEME_NATIVE_EXACT
from x402_tron.tokens import TokenInfo, TokenRegistry
from x402_tron.types import PaymentRequirements


@pytest.fixture(autouse=True)
def _register_test_token():
    TokenRegistry.register_token(
        "tron:nile",
        TokenInfo(address="TTestUSDTAddress", decimals=6, name="Test USDT", symbol="USDT"),
    )
    yield
    TokenRegistry._tokens.get("tron:nile", {}).pop("USDT", None)


@pytest.fixture
def mock_signer():
    signer = MagicMock()
    signer.get_address.return_value = "TTestBuyerAddress"
    signer.sign_typed_data = AsyncMock(return_value="0x" + "ab" * 65)
    return signer


@pytest.fixture
def nile_requirements():
    return PaymentRequirements(
        scheme="native_exact",
        network="tron:nile",
        amount="1000000",
        asset="TTestUSDTAddress",
        payTo="TTestMerchantAddress",
    )


class TestScheme:
    def test_scheme_returns_native_exact(self, mock_signer):
        mechanism = NativeExactTronClientMechanism(mock_signer)
        assert mechanism.scheme() == SCHEME_NATIVE_EXACT

    def test_get_signer(self, mock_signer):
        mechanism = NativeExactTronClientMechanism(mock_signer)
        assert mechanism.get_signer() is mock_signer


class TestCreatePaymentPayload:
    @pytest.mark.anyio
    async def test_payload_structure(self, mock_signer, nile_requirements):
        mechanism = NativeExactTronClientMechanism(mock_signer)
        payload = await mechanism.create_payment_payload(
            nile_requirements, "https://example.com/resource"
        )

        assert payload.x402_version == 2
        assert payload.resource.url == "https://example.com/resource"
        assert payload.accepted == nile_requirements
        assert payload.payload.signature == "0x" + "ab" * 65
        assert payload.payload.payment_permit is None

    @pytest.mark.anyio
    async def test_extensions_contain_authorization(self, mock_signer, nile_requirements):
        mechanism = NativeExactTronClientMechanism(mock_signer)
        payload = await mechanism.create_payment_payload(
            nile_requirements, "https://example.com/resource"
        )

        assert "transferAuthorization" in payload.extensions
        auth = payload.extensions["transferAuthorization"]
        assert auth["from"] == "TTestBuyerAddress"
        assert auth["to"] == "TTestMerchantAddress"
        assert auth["value"] == "1000000"
        assert "validAfter" in auth
        assert "validBefore" in auth
        assert "nonce" in auth

    @pytest.mark.anyio
    async def test_validity_window(self, mock_signer, nile_requirements):
        mechanism = NativeExactTronClientMechanism(mock_signer)
        payload = await mechanism.create_payment_payload(
            nile_requirements, "https://example.com/resource"
        )

        auth = payload.extensions["transferAuthorization"]
        now = int(time.time())
        assert int(auth["validAfter"]) <= now
        assert int(auth["validBefore"]) > now

    @pytest.mark.anyio
    async def test_nonce_is_unique(self, mock_signer, nile_requirements):
        mechanism = NativeExactTronClientMechanism(mock_signer)
        p1 = await mechanism.create_payment_payload(nile_requirements, "https://a.com")
        p2 = await mechanism.create_payment_payload(nile_requirements, "https://b.com")

        assert (
            p1.extensions["transferAuthorization"]["nonce"]
            != p2.extensions["transferAuthorization"]["nonce"]
        )

    @pytest.mark.anyio
    async def test_sign_typed_data_called(self, mock_signer, nile_requirements):
        mechanism = NativeExactTronClientMechanism(mock_signer)
        await mechanism.create_payment_payload(nile_requirements, "https://example.com")

        mock_signer.sign_typed_data.assert_called_once()
        call_kwargs = mock_signer.sign_typed_data.call_args.kwargs
        assert "domain" in call_kwargs
        assert "types" in call_kwargs
        assert "message" in call_kwargs

    @pytest.mark.anyio
    async def test_domain_uses_token_contract(self, mock_signer, nile_requirements):
        """verifyingContract should be the token address, not PaymentPermit"""
        mechanism = NativeExactTronClientMechanism(mock_signer)
        await mechanism.create_payment_payload(nile_requirements, "https://example.com")

        call_kwargs = mock_signer.sign_typed_data.call_args.kwargs
        domain = call_kwargs["domain"]
        assert domain["name"] == "Test USDT"
        assert domain["version"] == "1"
        # verifyingContract should be EVM format of token address
        assert domain["verifyingContract"].startswith("0x")

    @pytest.mark.anyio
    async def test_no_allowance_check(self, mock_signer, nile_requirements):
        """native_exact should NOT call check_allowance or ensure_allowance"""
        mechanism = NativeExactTronClientMechanism(mock_signer)
        await mechanism.create_payment_payload(nile_requirements, "https://example.com")

        assert not hasattr(mock_signer, "check_allowance") or not mock_signer.check_allowance.called
        assert (
            not hasattr(mock_signer, "ensure_allowance") or not mock_signer.ensure_allowance.called
        )
