"""
AgentWalletFacilitatorSigner - Facilitator signer backed by agent-wallet provider.

Standalone implementation that directly inherits from ``FacilitatorSigner``.
Signing is delegated to the provider wrapper; chain reads use a local
``AsyncTron`` client (same pattern as ``TronFacilitatorSigner``).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from x402_tron.abi import EIP712_DOMAIN_TYPE, PAYMENT_PERMIT_PRIMARY_TYPE
from x402_tron.signers.facilitator.base import FacilitatorSigner
from x402_tron.signers.provider_wrapper import BaseProviderWrapper, TronProviderWrapper

logger = logging.getLogger(__name__)


class AgentWalletFacilitatorSigner(FacilitatorSigner):
    """Facilitator signer that takes an agent-wallet provider directly.

    - **Signing** (sign_tx) → delegated to provider wrapper.
    - **Chain reads** (contract calls, tx receipts) → local ``AsyncTron`` client.
    - Private keys are never accessed by this class.

    Usage::

        from wallet import TronProvider
        from x402_tron.signers.facilitator import AgentWalletFacilitatorSigner

        provider = await TronProvider.create(private_key="deadbeef...")
        signer = await AgentWalletFacilitatorSigner.create(provider, network="tron:nile")
    """

    def __init__(self, wrapper: BaseProviderWrapper, network: str | None = None) -> None:
        self._wrapper = wrapper
        self._address: str | None = None  # resolved in create()
        self._network = network
        self._async_tron_clients: dict[str, Any] = {}

    @classmethod
    async def create(
        cls,
        provider: Any,
        network: str | None = None,
        *,
        wrapper: BaseProviderWrapper | None = None,
    ) -> "AgentWalletFacilitatorSigner":
        """Async factory — creates the wrapper and resolves address from provider."""
        if wrapper is None:
            wrapper = await TronProviderWrapper.create(provider)
        instance = cls(wrapper=wrapper, network=network)
        instance._address = await wrapper.get_address()
        logger.info("AgentWalletFacilitatorSigner initialized: address=%s", instance._address)
        return instance

    def _ensure_async_tron_client(self, network: str | None = None) -> Any:
        """Lazy initialize AsyncTron client for chain reads."""
        net = network or self._network
        if not net:
            return None
        if net not in self._async_tron_clients:
            try:
                from x402_tron.utils.tron_client import create_async_tron_client

                self._async_tron_clients[net] = create_async_tron_client(net)
            except ImportError:
                return None
        return self._async_tron_clients[net]

    def get_address(self) -> str:
        return self._address

    async def verify_typed_data(
        self,
        address: str,
        domain: dict[str, Any],
        types: dict[str, Any],
        message: dict[str, Any],
        signature: str,
    ) -> bool:
        """Verify EIP-712 signature.

        Note: Verification does not require private key access — it only
        recovers the signer address from the signature and compares it.
        """
        try:
            from eth_account import Account
            from eth_account.messages import encode_typed_data

            from x402_tron.utils.address import tron_address_to_evm

            full_types = {
                "EIP712Domain": EIP712_DOMAIN_TYPE,
                **types,
            }

            primary_type = PAYMENT_PERMIT_PRIMARY_TYPE

            message_copy = dict(message)
            if "meta" in message_copy and "paymentId" in message_copy["meta"]:
                payment_id = message_copy["meta"]["paymentId"]
                if isinstance(payment_id, str) and payment_id.startswith("0x"):
                    message_copy["meta"] = dict(message_copy["meta"])
                    message_copy["meta"]["paymentId"] = bytes.fromhex(payment_id[2:])

            typed_data = {
                "types": full_types,
                "primaryType": primary_type,
                "domain": domain,
                "message": message_copy,
            }

            signable = encode_typed_data(full_message=typed_data)

            sig_bytes = bytes.fromhex(signature[2:] if signature.startswith("0x") else signature)
            recovered = Account.recover_message(signable, signature=sig_bytes)

            expected_evm = tron_address_to_evm(address)

            logger.info(
                "Signature verification: expected_tron=%s, expected_evm=%s, recovered=%s",
                address,
                expected_evm,
                recovered,
            )

            return recovered.lower() == expected_evm.lower()
        except Exception as e:
            logger.error(f"Signature verification error: {e}", exc_info=True)
            return False

    def _normalize_tron_address(self, address: str) -> str:
        """Normalize TRON address to valid Base58Check format"""
        try:
            from tronpy.keys import to_base58check_address

            if address.startswith("0x") and len(address) == 42:
                hex_addr = "41" + address[2:].lower()
                return to_base58check_address(hex_addr)

            if address.startswith("T"):
                return address

            return address
        except Exception:
            return address

    async def write_contract(
        self,
        contract_address: str,
        abi: str,
        method: str,
        args: list[Any],
        network: str | None = None,
    ) -> str | None:
        """Execute contract transaction on TRON.

        Chain reads via local AsyncTron client, signing via provider wrapper.
        """
        import json as json_module

        net = network or self._network
        client = self._ensure_async_tron_client(net)
        if not client:
            logger.error(f"No AsyncTron client for network {net}")
            return None

        try:
            normalized_address = self._normalize_tron_address(contract_address)
            logger.info(f"Normalized contract address: {contract_address} -> {normalized_address}")

            # Log account resources before transaction
            try:
                account_info = await client.get_account(self._address)
                account_resource = await client.get_account_resource(self._address)
                logger.info(f"Account address: {self._address}")
                logger.info(
                    f"Account balance: {account_info.get('balance', 0) / 1_000_000:.6f} TRX"
                )
                logger.info("Account resources:")
                logger.info(f"  - freeNetLimit: {account_resource.get('freeNetLimit', 0)}")
                logger.info(f"  - freeNetUsed: {account_resource.get('freeNetUsed', 0)}")
                logger.info(f"  - NetLimit: {account_resource.get('NetLimit', 0)}")
                logger.info(f"  - NetUsed: {account_resource.get('NetUsed', 0)}")
                logger.info(f"  - EnergyLimit: {account_resource.get('EnergyLimit', 0)}")
                logger.info(f"  - EnergyUsed: {account_resource.get('EnergyUsed', 0)}")
                logger.info(f"  - TotalEnergyLimit: {account_resource.get('TotalEnergyLimit', 0)}")
                logger.info(
                    f"  - TotalEnergyWeight: {account_resource.get('TotalEnergyWeight', 0)}"
                )
            except Exception as resource_err:
                logger.warning(f"Failed to fetch account resources: {resource_err}")

            self._log_contract_parameters(method, args, logger)

            abi_list = json_module.loads(abi) if isinstance(abi, str) else abi
            contract = await client.get_contract(normalized_address)
            contract.abi = abi_list

            func = getattr(contract.functions, method)

            logger.info(f"Function: {method}")
            logger.info(f"  Signature: {func.function_signature}")
            logger.info(f"  Method ID: {func.function_signature_hash}")

            logger.info("Building transaction with fee_limit=1,000,000,000 SUN (1000 TRX)")
            txn_builder = await func(*args)
            txn_builder = txn_builder.with_owner(self._address).fee_limit(1_000_000_000)
            txn = await txn_builder.build()

            # Sign via provider wrapper (no private key access)
            result = await self._wrapper.sign_tx(txn)
            signed_txn = result["signed_tx"]

            # Log transaction details before broadcast
            try:
                txn_dict = signed_txn.to_json()
                logger.info("Transaction built successfully:")
                logger.info(f"  - txID: {txn_dict.get('txID', 'N/A')}")
                logger.info(f"  - raw_data_hex length: {len(txn_dict.get('raw_data_hex', ''))}")
                logger.info(
                    f"  - fee_limit: {txn_dict.get('raw_data', {}).get('fee_limit', 'N/A')}"
                )
            except Exception as log_err:
                logger.warning(f"Failed to log transaction details: {log_err}")

            logger.info("Broadcasting transaction...")
            broadcast_result = await signed_txn.broadcast()
            logger.info(f"Transaction broadcast successful: {broadcast_result}")
            return broadcast_result.get("txid")
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"Contract call failed: [{error_type}] {error_msg}")

            if "BANDWITH_ERROR" in error_msg or "bandwidth" in error_msg.lower():
                logger.error(
                    "BANDWIDTH ERROR: The account does not have enough bandwidth to "
                    "broadcast the transaction."
                )
                logger.error("Solutions:")
                logger.error("  1. Wait for bandwidth to regenerate (24 hours for free bandwidth)")
                logger.error("  2. Stake TRX to get more bandwidth")
                logger.error(
                    "  3. Burn TRX to pay for bandwidth (transaction will consume TRX balance)"
                )
                logger.error("  4. Use a different account with available bandwidth")
            elif "ENERGY" in error_msg:
                logger.error(
                    "ENERGY ERROR: The account does not have enough energy to execute the contract."
                )
                logger.error("Solutions:")
                logger.error("  1. Stake TRX to get energy")
                logger.error("  2. Burn TRX to pay for energy")
            elif "balance" in error_msg.lower():
                logger.error("BALANCE ERROR: The account does not have enough TRX balance.")
                logger.error("Solution: Add TRX to the account")

            logger.error("Full exception details:", exc_info=True)
            return None

    def _log_contract_parameters(self, method: str, args: list[Any], logger: Any) -> None:
        """Log contract call parameters as a complete JSON"""
        try:
            import json

            def serialize_value(value: Any) -> Any:
                """Recursively convert values to JSON-serializable format"""
                if isinstance(value, bytes):
                    return f"0x{value.hex()}"
                elif isinstance(value, (tuple, list)):
                    return [serialize_value(item) for item in value]
                elif isinstance(value, dict):
                    return {k: serialize_value(v) for k, v in value.items()}
                elif isinstance(value, int):
                    return {"decimal": value, "hex": f"0x{value:x}"}
                elif isinstance(value, str):
                    return value
                else:
                    return str(value)

            contract_call = {"method": method, "arguments": [serialize_value(arg) for arg in args]}

            json_output = json.dumps(contract_call, indent=2, ensure_ascii=False)
            logger.info(
                f"\n{'=' * 80}\nContract Call Parameters:\n{'=' * 80}\n{json_output}\n{'=' * 80}"
            )
        except Exception as e:
            logger.warning(f"Failed to log contract parameters: {e}")

    async def wait_for_transaction_receipt(
        self,
        tx_hash: str,
        timeout: int = 60,
        network: str | None = None,
    ) -> dict[str, Any]:
        """Wait for TRON transaction confirmation (async with 60s default timeout)"""
        net = network or self._network
        client = self._ensure_async_tron_client(net)
        if not client:
            raise RuntimeError(f"No AsyncTron client for network {net}")

        start = time.time()
        while time.time() - start < timeout:
            try:
                info = await client.get_transaction_info(tx_hash)
                if info and info.get("blockNumber"):
                    return {
                        "hash": tx_hash,
                        "blockNumber": str(info.get("blockNumber")),
                        "status": "confirmed"
                        if info.get("receipt", {}).get("result") == "SUCCESS"
                        else "failed",
                    }
            except Exception:
                pass
            await asyncio.sleep(3)

        raise TimeoutError(f"Transaction {tx_hash} not confirmed within {timeout}s")
