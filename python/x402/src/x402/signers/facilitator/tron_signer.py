"""
TronFacilitatorSigner - TRON facilitator 签名器实现
"""

import json
import time
from typing import Any

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

            full_types = {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                **types,
            }

            # Determine primaryType from types dict
            primary_type = "PaymentPermit"
            
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
        
        对于 ABIEncoderV2 合约（如 permitTransferFrom），需要手动编码以确保 MethodID 正确。
        链上合约使用 ABIEncoderV2，MethodID 计算时 tuple 被当作 ()。
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
            
            # 对于 permitTransferFrom，使用手动编码以确保 MethodID 正确
            # 链上合约使用 ABIEncoderV2，MethodID 计算时 tuple 被当作 ()
            if method == "permitTransferFrom":
                call_data = self._encode_permit_transfer_from(args, logger)
                return await self._send_raw_transaction(
                    client, normalized_address, call_data, logger
                )
            elif method == "permitTransferFromWithCallback":
                call_data = self._encode_permit_transfer_from_with_callback(args, logger)
                return await self._send_raw_transaction(
                    client, normalized_address, call_data, logger
                )
            
            # 其他方法使用 tronpy 标准方式
            abi_list = json_module.loads(abi) if isinstance(abi, str) else abi
            contract = client.get_contract(normalized_address)
            contract.abi = abi_list
            
            func = getattr(contract.functions, method)
            txn = (
                func(*args)
                .with_owner(self._address)
                .fee_limit(1_000_000_000)
                .build()
                .sign(PrivateKey(bytes.fromhex(self._private_key)))
            )
            
            self._log_transaction_as_curl(txn, client, logger)
            result = txn.broadcast()
            return result.get("txid")
        except Exception as e:
            logger.error(f"Contract call failed: {e}", exc_info=True)
            return None
    
    async def _send_raw_transaction(
        self, client: Any, contract_address: str, call_data: str, logger: Any
    ) -> str | None:
        """使用 tronpy 发送手动编码的交易"""
        from tronpy.keys import PrivateKey, to_hex_address
        
        owner_hex = to_hex_address(self._address)
        contract_hex = to_hex_address(contract_address)
        
        logger.info(f"Building TriggerSmartContract transaction")
        logger.info(f"  Owner: {self._address} -> {owner_hex}")
        logger.info(f"  Contract: {contract_address} -> {contract_hex}")
        logger.info(f"  Call data (first 100 chars): {call_data[:100]}...")
        
        # 使用 tronpy 的内部 API 构建交易
        txn = (
            client.trx._build_transaction(
                "TriggerSmartContract",
                {
                    "owner_address": owner_hex,
                    "contract_address": contract_hex,
                    "data": call_data,
                    "call_value": 0,
                }
            )
            .fee_limit(1_000_000_000)
            .build()
            .sign(PrivateKey(bytes.fromhex(self._private_key)))
        )
        
        self._log_transaction_as_curl(txn, client, logger)
        result = txn.broadcast()
        return result.get("txid")
    
    def _encode_permit_transfer_from(self, args: list[Any], logger: Any) -> str:
        """编码 permitTransferFrom 调用数据
        
        MethodID: 8c1b8baa
        函数签名: permitTransferFrom(tuple,tuple,address,bytes)
        """
        from eth_abi import encode
        from Crypto.Hash import keccak
        import base58
        
        # 正确的函数签名
        function_signature = "permitTransferFrom(tuple,tuple,address,bytes)"
        k = keccak.new(digest_bits=256)
        k.update(function_signature.encode())
        method_id = k.hexdigest()[:8]
        
        logger.info(f"Calculated MethodID: {method_id} (expected: 8c1b8baa)")
        
        permit_tuple = args[0]
        transfer_details = args[1]
        owner = args[2]
        signature = args[3]
        
        def tron_to_evm(tron_addr: str) -> str:
            if isinstance(tron_addr, str) and tron_addr.startswith("T"):
                decoded = base58.b58decode(tron_addr)
                return "0x" + decoded[1:21].hex()
            return tron_addr
        
        meta = permit_tuple[0]
        permit_encoded = (
            meta,
            tron_to_evm(permit_tuple[1]),
            tron_to_evm(permit_tuple[2]),
            (
                tron_to_evm(permit_tuple[3][0]),
                permit_tuple[3][1],
                tron_to_evm(permit_tuple[3][2]),
            ),
            (
                tron_to_evm(permit_tuple[4][0]),
                permit_tuple[4][1],
            ),
            (
                tron_to_evm(permit_tuple[5][0]),
                permit_tuple[5][1],
                permit_tuple[5][2],
            ),
        )
        
        owner_evm = tron_to_evm(owner)
        
        logger.info(f"Encoding permitTransferFrom with MethodID: {method_id}")
        logger.info(f"  permit: {permit_encoded}")
        logger.info(f"  transferDetails: {transfer_details}")
        logger.info(f"  owner: {owner_evm}")
        logger.info(f"  signature length: {len(signature)} bytes")
        
        encoded_params = encode(
            [
                "((uint8,bytes16,uint256,uint256,uint256),address,address,(address,uint256,address),(address,uint256),(address,uint256,uint256))",
                "(uint256)",
                "address",
                "bytes"
            ],
            [permit_encoded, transfer_details, owner_evm, signature]
        )
        
        return method_id + encoded_params.hex()
    
    def _encode_permit_transfer_from_with_callback(self, args: list[Any], logger: Any) -> str:
        """编码 permitTransferFromWithCallback 调用数据
        
        函数签名: permitTransferFromWithCallback(tuple,tuple,tuple,address,bytes)
        """
        from eth_abi import encode
        from Crypto.Hash import keccak
        import base58
        
        function_signature = "permitTransferFromWithCallback(tuple,tuple,tuple,address,bytes)"
        k = keccak.new(digest_bits=256)
        k.update(function_signature.encode())
        method_id = k.hexdigest()[:8]
        
        permit_tuple = args[0]
        callback_details = args[1]
        transfer_details = args[2]
        owner = args[3]
        signature = args[4]
        
        def tron_to_evm(tron_addr: str) -> str:
            if isinstance(tron_addr, str) and tron_addr.startswith("T"):
                decoded = base58.b58decode(tron_addr)
                return "0x" + decoded[1:21].hex()
            return tron_addr
        
        meta = permit_tuple[0]
        permit_encoded = (
            meta,
            tron_to_evm(permit_tuple[1]),
            tron_to_evm(permit_tuple[2]),
            (
                tron_to_evm(permit_tuple[3][0]),
                permit_tuple[3][1],
                tron_to_evm(permit_tuple[3][2]),
            ),
            (
                tron_to_evm(permit_tuple[4][0]),
                permit_tuple[4][1],
            ),
            (
                tron_to_evm(permit_tuple[5][0]),
                permit_tuple[5][1],
                permit_tuple[5][2],
            ),
        )
        
        callback_encoded = (
            tron_to_evm(callback_details[0]),
            callback_details[1],
        )
        
        owner_evm = tron_to_evm(owner)
        
        logger.info(f"Encoding permitTransferFromWithCallback with MethodID: {method_id}")
        
        encoded_params = encode(
            [
                "((uint8,bytes16,uint256,uint256,uint256),address,address,(address,uint256,address),(address,uint256),(address,uint256,uint256))",
                "(address,bytes)",
                "(uint256)",
                "address",
                "bytes"
            ],
            [permit_encoded, callback_encoded, transfer_details, owner_evm, signature]
        )
        
        return method_id + encoded_params.hex()
    
    def _log_contract_parameters(self, method: str, args: list[Any], logger: Any) -> None:
        """Log contract call parameters in detail"""
        try:
            output_lines = [
                "========================================",
                "Contract Call Parameters:",
                "========================================",
                f"Method: {method}",
                f"Number of arguments: {len(args)}",
            ]
            
            for i, arg in enumerate(args):
                output_lines.append(f"\nArgument {i}:")
                self._format_parameter_value(arg, output_lines, indent=2)
            
            output_lines.append("\n========================================\n")
            
            # Output all at once
            logger.info("\n".join(output_lines))
        except Exception as e:
            logger.warning(f"Failed to log contract parameters: {e}")
    
    def _format_parameter_value(self, value: Any, output_lines: list[str], indent: int = 0) -> None:
        """Recursively format parameter values with proper formatting"""
        indent_str = " " * indent
        
        if isinstance(value, (tuple, list)):
            output_lines.append(f"{indent_str}Type: {type(value).__name__}, Length: {len(value)}")
            for i, item in enumerate(value):
                output_lines.append(f"{indent_str}  [{i}]:")
                self._format_parameter_value(item, output_lines, indent + 4)
        elif isinstance(value, bytes):
            output_lines.append(f"{indent_str}Type: bytes, Length: {len(value)}")
            output_lines.append(f"{indent_str}Hex: 0x{value.hex()}")
        elif isinstance(value, str):
            output_lines.append(f"{indent_str}Type: str, Value: {value}")
        elif isinstance(value, int):
            output_lines.append(f"{indent_str}Type: int, Value: {value} (0x{value:x})")
        elif isinstance(value, dict):
            output_lines.append(f"{indent_str}Type: dict, Keys: {list(value.keys())}")
            for key, val in value.items():
                output_lines.append(f"{indent_str}  {key}:")
                self._format_parameter_value(val, output_lines, indent + 4)
        else:
            output_lines.append(f"{indent_str}Type: {type(value).__name__}, Value: {value}")
    
    def _log_transaction_as_curl(self, txn: Any, client: Any, logger: Any) -> None:
        """Log transaction as curl command for debugging"""
        try:
            # Get the transaction as dict
            tx_dict = txn.to_json() if hasattr(txn, 'to_json') else txn
            
            # If it's a string, parse it
            if isinstance(tx_dict, str):
                tx_dict = json.loads(tx_dict)
            
            # Determine the API endpoint based on network
            network = getattr(client, 'network', 'nile')
            if network == 'mainnet':
                api_url = "https://api.trongrid.io/wallet/broadcasttransaction"
            elif network == 'shasta':
                api_url = "https://api.shasta.trongrid.io/wallet/broadcasttransaction"
            else:  # nile or default
                api_url = "https://nile.trongrid.io/wallet/broadcasttransaction"
            
            # Convert to formatted JSON string
            tx_json_str = json.dumps(tx_dict, indent=2)
            
            # For curl command, use compact JSON (no newlines)
            tx_json_compact = json.dumps(tx_dict)
            
            # Format as curl command
            curl_cmd = f"""
========================================
TRON Transaction as curl command:
========================================
curl -X POST '{api_url}' \\
  -H 'Content-Type: application/json' \\
  -d '{tx_json_compact}'

========================================
Raw transaction JSON (formatted):
========================================
{tx_json_str}
========================================
"""
            logger.info(curl_cmd)
            
        except Exception as e:
            logger.warning(f"Failed to log transaction as curl: {e}")

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
