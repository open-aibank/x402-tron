"""
Tests for AgentWalletClientSigner and AgentWalletFacilitatorSigner.

Signer takes a provider directly (TronProvider / FlashProvider).
Provider handles keystore internally — signer doesn't know about it.
Private keys are never extracted — all signing goes through the provider wrapper.
"""

import pytest

from x402_tron.signers.key_provider import KeyProvider
from x402_tron.signers.adapter import TronProviderAdapter
from x402_tron.signers.provider_wrapper import TronProviderWrapper, BaseProviderWrapper
from x402_tron.signers.agent_wallet_provider import create_tron_provider
from x402_tron.signers.client import AgentWalletClientSigner
from x402_tron.signers.facilitator import AgentWalletFacilitatorSigner


TEST_PRIVATE_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


class MockTronProvider:
    """Mimics agent-wallet's BaseProvider for testing.

    Only exposes the provider's public interface:
    - get_account_info(): returns {"address": ...}
    - sign_tx(unsigned_tx): returns {"signed_tx": ..., "signature": None}
    - sign_message(message): returns hex-encoded signature
    """

    def __init__(self, private_key: str):
        from tronpy.keys import PrivateKey

        clean = private_key[2:] if private_key.startswith("0x") else private_key
        pk = PrivateKey(bytes.fromhex(clean))
        self.address = pk.public_key.to_base58check_address()

    async def get_account_info(self):
        return {"address": self.address}

    async def sign_tx(self, unsigned_tx):
        return {"signed_tx": unsigned_tx, "signature": None}

    async def sign_message(self, message: bytes) -> str:
        return "ab" * 65  # mock 65-byte signature hex


# --- TronProviderAdapter ---


@pytest.mark.asyncio
async def test_adapter_satisfies_protocol():
    mock = MockTronProvider(TEST_PRIVATE_KEY)
    adapter = await TronProviderAdapter.create(mock)
    assert isinstance(adapter, KeyProvider)


@pytest.mark.asyncio
async def test_adapter_get_address():
    mock = MockTronProvider(TEST_PRIVATE_KEY)
    adapter = await TronProviderAdapter.create(mock)
    assert adapter.get_address().startswith("T")


@pytest.mark.asyncio
async def test_adapter_raises_on_missing_address():
    mock = MockTronProvider(TEST_PRIVATE_KEY)
    mock.address = None
    with pytest.raises(ValueError, match="no address"):
        await TronProviderAdapter.create(mock)


# --- TronProviderWrapper ---


@pytest.mark.asyncio
async def test_wrapper_get_address():
    mock = MockTronProvider(TEST_PRIVATE_KEY)
    wrapper = await TronProviderWrapper.create(mock)
    address = await wrapper.get_address()
    assert address.startswith("T")
    assert address == mock.address


@pytest.mark.asyncio
async def test_wrapper_sign_tx():
    mock = MockTronProvider(TEST_PRIVATE_KEY)
    wrapper = await TronProviderWrapper.create(mock)
    result = await wrapper.sign_tx({"raw": "tx_data"})
    assert result["signed_tx"] == {"raw": "tx_data"}
    assert result["signature"] is None


@pytest.mark.asyncio
async def test_wrapper_raises_on_missing_address():
    mock = MockTronProvider(TEST_PRIVATE_KEY)
    mock.address = None
    with pytest.raises(ValueError, match="no address"):
        await TronProviderWrapper.create(mock)


@pytest.mark.asyncio
async def test_wrapper_sign_message():
    mock = MockTronProvider(TEST_PRIVATE_KEY)
    wrapper = await TronProviderWrapper.create(mock)
    sig = await wrapper.sign_message(b"hello")
    assert isinstance(sig, str)
    assert len(sig) > 0


# --- AgentWalletClientSigner ---


@pytest.mark.asyncio
async def test_client_signer_from_provider():
    mock = MockTronProvider(TEST_PRIVATE_KEY)
    signer = await AgentWalletClientSigner.create(mock)
    assert signer.get_address().startswith("T")
    assert signer.get_address() == mock.address


@pytest.mark.asyncio
async def test_client_signer_same_address_as_tron_signer():
    from x402_tron.signers.client import TronClientSigner

    mock = MockTronProvider(TEST_PRIVATE_KEY)
    tron_signer = TronClientSigner(TEST_PRIVATE_KEY)
    agent_signer = await AgentWalletClientSigner.create(mock)
    assert agent_signer.get_address() == tron_signer.get_address()


@pytest.mark.asyncio
async def test_client_signer_with_network():
    mock = MockTronProvider(TEST_PRIVATE_KEY)
    signer = await AgentWalletClientSigner.create(mock, network="tron:nile")
    assert signer.get_address() == mock.address


# --- AgentWalletFacilitatorSigner ---


@pytest.mark.asyncio
async def test_facilitator_signer_from_provider():
    mock = MockTronProvider(TEST_PRIVATE_KEY)
    signer = await AgentWalletFacilitatorSigner.create(mock)
    assert signer.get_address().startswith("T")
    assert signer.get_address() == mock.address


@pytest.mark.asyncio
async def test_facilitator_signer_same_address_as_tron_signer():
    from x402_tron.signers.facilitator import TronFacilitatorSigner

    mock = MockTronProvider(TEST_PRIVATE_KEY)
    tron_signer = TronFacilitatorSigner(TEST_PRIVATE_KEY)
    agent_signer = await AgentWalletFacilitatorSigner.create(mock)
    assert agent_signer.get_address() == tron_signer.get_address()


@pytest.mark.asyncio
async def test_facilitator_signer_with_network():
    mock = MockTronProvider(TEST_PRIVATE_KEY)
    signer = await AgentWalletFacilitatorSigner.create(mock, network="tron:nile")
    assert signer.get_address() == mock.address


@pytest.mark.asyncio
async def test_create_tron_provider(monkeypatch):
    class DummyProvider:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        @classmethod
        async def create(cls, **kwargs):
            return cls(**kwargs)

    monkeypatch.setitem(__import__("sys").modules, "wallet", type("M", (), {"TronProvider": DummyProvider}))
    provider = await create_tron_provider(private_key="deadbeef")
    assert provider.kwargs["private_key"] == "deadbeef"
