"""
TronFacilitatorSigner - TRON facilitator 签名器实现
"""

import json
import time
from typing import Any

from x402.abi import PAYMENT_PERMIT_PRIMARY_TYPE, EIP712_DOMAIN_TYPE
from x402.signers.facilitator.base import FacilitatorSigner


class TronFacilitatorSigner(FacilitatorSigner):
    """TRON facilitator 签名器实现"""

    def __init__(self, private_key: str, network: str | None = None) -> None:
        clean_key = private_key[2:] if private_key.startswith("0x") else private_key
        self._private_key = clean_key
        self._address = self._derive_address(clean_key)
        self._network = network
        self._tron_client: Any = None

    @classmethod
    def from_private_key(cls, private_key: str, network: str | None = None) -> "TronFacilitatorSigner":
        """从私钥创建签名器"""
        return cls(private_key, network)

    def _ensure_tron_client(self) -> Any:
        """延迟初始化 tron_client"""
        if self._tron_client is None and self._network:
            try:
                from tronpy import Tron
                self._tron_client = Tron(network=self._network)
            except ImportError:
                pass
        return self._tron_client

    @staticmethod
    def _derive_address(private_key: str) -> str:
        """从私钥派生 TRON 地址"""
        try:
            from tronpy.keys import PrivateKey
            pk = PrivateKey(bytes.fromhex(private_key))
            return pk.public_key.to_base58check_address()
        except ImportError:
            return f"T{private_key[:33]}"

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
        """验证 EIP-712 签名"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            from eth_account import Account
            from eth_account.messages import encode_typed_data

            # Note: PaymentPermit contract uses EIP712Domain WITHOUT version field
            # Contract: keccak256("EIP712Domain(string name,uint256 chainId,address verifyingContract)")
            full_types = {
                "EIP712Domain": EIP712_DOMAIN_TYPE,
                **types,
            }

            primary_type = PAYMENT_PERMIT_PRIMARY_TYPE
            
            typed_data = {
                "types": full_types,
                "primaryType": primary_type,
                "domain": domain,
                "message": message,
            }

            signable = encode_typed_data(full_message=typed_data)
            
            sig_bytes = bytes.fromhex(signature[2:] if signature.startswith("0x") else signature)
            recovered = Account.recover_message(signable, signature=sig_bytes)

            logger.info(f"Signature verification: expected={address}, recovered={recovered}")
            tron_address = self._evm_to_tron_address(recovered)
            logger.info(f"Converted to TRON: expected_tron={address}, recovered_tron={tron_address}")
            
            return tron_address.lower() == address.lower()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Signature verification error: {e}")
            return False

    def _evm_to_tron_address(self, evm_address: str) -> str:
        """Convert EVM address to TRON address"""
        try:
            from tronpy.keys import to_base58check_address
            hex_addr = "41" + evm_address[2:].lower()
            return to_base58check_address(hex_addr)
        except ImportError:
            return evm_address

    def _normalize_tron_address(self, address: str) -> str:
        """Normalize TRON address to valid Base58Check format"""
        try:
            from tronpy.keys import to_base58check_address
            
            # If it's a hex address (0x...), convert to TRON address
            if address.startswith("0x") and len(address) == 42:
                hex_addr = "41" + address[2:].lower()
                return to_base58check_address(hex_addr)
            
            # If it starts with T, assume it's already a valid TRON address
            if address.startswith("T"):
                return address
            
            # Otherwise return as-is
            return address
        except Exception:
            return address

    async def write_contract(
        self,
        contract_address: str,
        abi: str,
        method: str,
        args: list[Any],
    ) -> str | None:
        """在 TRON 上执行合约交易
        
        使用 tronpy 原生功能处理 ABI 和 Method ID 计算
        """
        import logging
        import json as json_module
        from tronpy.keys import PrivateKey
        
        logger = logging.getLogger(__name__)
        
        client = self._ensure_tron_client()
        if client is None:
            raise RuntimeError("tronpy client required for contract calls")

        try:
            # Normalize contract address to ensure valid Base58Check format
            normalized_address = self._normalize_tron_address(contract_address)
            logger.debug(f"Normalized contract address: {contract_address} -> {normalized_address}")
            
            # Log contract call parameters in detail
            self._log_contract_parameters(method, args, logger)
            
            # 使用 tronpy 标准方式 - 让 tronpy 自己计算 Method ID
            abi_list = json_module.loads(abi) if isinstance(abi, str) else abi
            contract = client.get_contract(normalized_address)
            contract.abi = abi_list
            
            # 获取函数对象
            func = getattr(contract.functions, method)
            
            # 记录 tronpy 计算的 Method ID
            logger.info(f"Function: {method}")
            logger.info(f"  Signature: {func.function_signature}")
            logger.info(f"  Method ID: {func.function_signature_hash}")
            
            # 构建并签名交易
            txn = (
                func(*args)
                .with_owner(self._address)
                .fee_limit(1_000_000_000)
                .build()
                .sign(PrivateKey(bytes.fromhex(self._private_key)))
            )
            
            result = txn.broadcast()
            return result.get("txid")
        except Exception as e:
            logger.error(f"Contract call failed: {e}", exc_info=True)
            return None
    
    def _log_contract_parameters(self, method: str, args: list[Any], logger: Any) -> None:
        """Log contract call parameters as a complete JSON"""
        try:
            import json
            
            # Convert arguments to JSON-serializable format
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
            
            # Build the complete parameter structure
            contract_call = {
                "method": method,
                "arguments": [serialize_value(arg) for arg in args]
            }
            
            # Output as formatted JSON
            json_output = json.dumps(contract_call, indent=2, ensure_ascii=False)
            logger.info(f"\n{'='*80}\nContract Call Parameters:\n{'='*80}\n{json_output}\n{'='*80}")
        except Exception as e:
            logger.warning(f"Failed to log contract parameters: {e}")
    
    async def wait_for_transaction_receipt(
        self,
        tx_hash: str,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """等待 TRON 交易确认"""
        client = self._ensure_tron_client()
        if client is None:
            raise RuntimeError("tronpy client required")

        start = time.time()
        while time.time() - start < timeout:
            try:
                info = client.get_transaction_info(tx_hash)
                if info and info.get("blockNumber"):
                    return {
                        "hash": tx_hash,
                        "blockNumber": str(info.get("blockNumber")),
                        "status": "confirmed" if info.get("receipt", {}).get("result") == "SUCCESS" else "failed",
                    }
            except Exception:
                pass
            time.sleep(3)

        raise TimeoutError(f"Transaction {tx_hash} not confirmed within {timeout}s")
