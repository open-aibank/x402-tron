/**
 * EvmClientSigner - EVM client signer for x402 protocol
 *
 * Uses viem for EIP-712 compatible signing.
 */

import {
  createWalletClient,
  createPublicClient,
  http,
  type WalletClient,
  type PublicClient,
  type Account,
  type Hex,
  parseAbi,
  type Hash,
  type Transport,
  type Chain,
} from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { mainnet, sepolia, bsc, bscTestnet } from 'viem/chains';
import type { ClientSigner } from '../client/x402Client.js';
import {
  getPaymentPermitAddress,
  InsufficientAllowanceError,
  UnsupportedNetworkError,
} from '../index.js';

// ERC20 ABI subset for allowance/approve/balanceOf
const ERC20_ABI = parseAbi([
  'function allowance(address owner, address spender) view returns (uint256)',
  'function approve(address spender, uint256 amount) returns (bool)',
  'function balanceOf(address account) view returns (uint256)',
]);

export class EvmClientSigner implements ClientSigner {
  private walletClient: WalletClient<Transport, Chain, Account>;
  private publicClients: Map<number, PublicClient> = new Map();
  private account: Account;

  /**
   * Create a new EvmClientSigner
   * @param privateKey - Private key in hex format (0x...)
   * @param rpcUrl - Optional RPC URL (if not provided, uses public RPCs)
   */
  constructor(privateKey: string, rpcUrl?: string) {
    if (!privateKey.startsWith('0x')) {
      privateKey = `0x${privateKey}`;
    }
    this.account = privateKeyToAccount(privateKey as Hex);

    // Initialize with a default chain (e.g., mainnet) but it can switch per request
    // Note: The wallet client is mainly for signing, chain context is passed in methods or derived
    this.walletClient = createWalletClient({
      account: this.account,
      chain: mainnet, // Default, overridden in requests if needed
      transport: http(rpcUrl),
    });
  }

  /**
   * Get the signer's address
   */
  getAddress(): string {
    return this.account.address;
  }

  /**
   * Get the signer's address as EVM Hex
   */
  getEvmAddress(): Hex {
    return this.account.address;
  }

  /**
   * Sign a raw message
   */
  async signMessage(message: Uint8Array): Promise<string> {
    return this.walletClient.signMessage({
      message: { raw: message },
    });
  }

  /**
   * Sign EIP-712 typed data
   */
  async signTypedData(
    domain: Record<string, unknown>,
    types: Record<string, unknown>,
    message: Record<string, unknown>,
  ): Promise<string> {
    // Viem expects types in a specific format
    // We need to cast the types to match viem's expectation
    // Note: This assumes the caller provides types in a format compatible with viem
    // The types argument from x402 SDK matches the EIP-712 standard structure

    // Extract primaryType from types keys (heuristic: prioritize PaymentPermitDetails)
    const primaryType = types.PaymentPermitDetails
      ? 'PaymentPermitDetails'
      : Object.keys(types).pop();

    if (!primaryType) {
      throw new Error('No primary type found in types definition');
    }

    // TODO: Update interface to accept primary_type explicitly.

    return this.walletClient.signTypedData({
      domain: domain as any,
      types: types as any,
      primaryType,
      message: message as any,
    });
  }

  /**
   * Check token balance
   */
  async checkBalance(token: string, network: string): Promise<bigint> {
    const chainId = this.parseNetworkToChainId(network);
    const client = this.getPublicClient(chainId);

    try {
      const balance = await client.readContract({
        address: token as Hex,
        abi: ERC20_ABI,
        functionName: 'balanceOf',
        args: [this.account.address],
      });
      return balance;
    } catch (error) {
      console.error(`[EvmClientSigner] Failed to check balance: ${error}`);
      return 0n;
    }
  }

  /**
   * Check token allowance
   */
  async checkAllowance(
    token: string,
    _amount: bigint,
    network: string,
  ): Promise<bigint> {
    const chainId = this.parseNetworkToChainId(network);
    const client = this.getPublicClient(chainId);
    const spender = getPaymentPermitAddress(network) as Hex;

    try {
      const allowance = await client.readContract({
        address: token as Hex,
        abi: ERC20_ABI,
        functionName: 'allowance',
        args: [this.account.address, spender],
      });
      return allowance;
    } catch (error) {
      console.error(`[EvmClientSigner] Failed to check allowance: ${error}`);
      return 0n;
    }
  }

  /**
   * Ensure sufficient allowance
   */
  async ensureAllowance(
    token: string,
    amount: bigint,
    network: string,
    mode: 'auto' | 'interactive' | 'skip' = 'auto',
  ): Promise<boolean> {
    if (mode === 'skip') {
      return true;
    }

    const currentAllowance = await this.checkAllowance(token, amount, network);
    if (currentAllowance >= amount) {
      return true;
    }

    if (mode === 'interactive') {
      throw new InsufficientAllowanceError(
        'Interactive approval not implemented',
      );
    }

    // Auto mode: send approve transaction
    console.log(
      `[EvmClientSigner] Approving ${amount} for ${token} on ${network}...`,
    );

    const chainId = this.parseNetworkToChainId(network);
    const client = this.getPublicClient(chainId);
    const spender = getPaymentPermitAddress(network) as Hex;
    const chain = this.getChain(chainId);

    try {
      // Switch wallet client chain if needed
      // Note: creating a new wallet client for the specific chain to ensure correct signing context
      const walletClient = createWalletClient({
        account: this.account,
        chain: chain,
        transport: http(),
      });

      const hash = await walletClient.writeContract({
        address: token as Hex,
        abi: ERC20_ABI,
        functionName: 'approve',
        args: [spender, BigInt(2) ** BigInt(256) - BigInt(1)], // Max approval
      });

      console.log(`[EvmClientSigner] Approve tx sent: ${hash}`);

      const receipt = await client.waitForTransactionReceipt({ hash });

      if (receipt.status === 'success') {
        console.log(`[EvmClientSigner] Approve confirmed`);
        return true;
      } else {
        console.error(`[EvmClientSigner] Approve failed`);
        return false;
      }
    } catch (error) {
      console.error(`[EvmClientSigner] Approve transaction failed: ${error}`);
      return false;
    }
  }

  /**
   * Helper to get public client for a chain
   */
  private getPublicClient(chainId: number): PublicClient {
    if (!this.publicClients.has(chainId)) {
      const chain = this.getChain(chainId);
      this.publicClients.set(
        chainId,
        createPublicClient({
          chain,
          transport: http(),
        }),
      );
    }
    return this.publicClients.get(chainId)!;
  }

  /**
   * Helper to get chain definition from chain ID
   */
  private getChain(chainId: number): Chain {
    const chains: Record<number, Chain> = {
      1: mainnet,
      11155111: sepolia,
      56: bsc,
      97: bscTestnet,
    };

    const chain = chains[chainId];
    if (!chain) {
      throw new UnsupportedNetworkError(`Unsupported EVM chain ID: ${chainId}`);
    }
    return chain;
  }

  /**
   * Parse network string (eip155:1) to chain ID (1)
   */
  private parseNetworkToChainId(network: string): number {
    if (!network.startsWith('eip155:')) {
      throw new UnsupportedNetworkError(
        `Invalid EVM network format: ${network}`,
      );
    }
    const chainId = parseInt(network.split(':')[1], 10);
    if (isNaN(chainId)) {
      throw new UnsupportedNetworkError(`Invalid EVM chain ID in: ${network}`);
    }
    return chainId;
  }
}
