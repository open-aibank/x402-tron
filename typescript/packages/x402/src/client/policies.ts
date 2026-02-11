/**
 * Payment policies for filtering or reordering payment requirements.
 *
 * Policies are applied in order after mechanism filtering and before token selection.
 */

import { findByAddress } from '../tokens.js';
import type { PaymentRequirements } from '../types/index.js';
import type { ClientSigner, PaymentPolicy } from './x402Client.js';

function getDecimals(req: PaymentRequirements): number {
  const token = findByAddress(req.network, req.asset);
  return token?.decimals ?? 6;
}

/** Entry mapping a network pattern to a signer */
interface SignerEntry {
  pattern: string;
  signer: ClientSigner;
}

function matchPattern(pattern: string, network: string): boolean {
  if (pattern === network) return true;
  if (pattern.endsWith(':*')) {
    return network.startsWith(pattern.slice(0, -1));
  }
  return false;
}

/**
 * Policy that filters out requirements with insufficient balance.
 *
 * When the server accepts multiple tokens (e.g. USDT and USDD),
 * this policy checks the user's on-chain balance for each option
 * and removes requirements the user cannot afford.
 *
 * Supports multi-network setups: pass a single signer for single-network
 * use, or a Record<networkPattern, signer> for multi-network.
 *
 * Requirements whose network has no matching signer are kept as-is
 * (not filtered out), so downstream mechanism matching can still work.
 *
 * If all requirements are unaffordable, returns an empty array so the
 * caller can raise an appropriate error.
 */
export class SufficientBalancePolicy implements PaymentPolicy {
  private signers: SignerEntry[];

  /**
   * @param signers - A single ClientSigner (legacy), or a
   *   Record<networkPattern, ClientSigner> for multi-network support.
   *   Network patterns follow the same syntax as X402Client.register()
   *   (e.g. "tron:*", "eip155:97").
   */
  constructor(signers: ClientSigner | Record<string, ClientSigner>) {
    if (typeof signers === 'object' && !('checkBalance' in signers)) {
      this.signers = Object.entries(signers as Record<string, ClientSigner>).map(
        ([pattern, signer]) => ({ pattern, signer })
      );
    } else {
      this.signers = [{ pattern: '*', signer: signers as ClientSigner }];
    }
  }

  private findSigner(network: string): ClientSigner | null {
    for (const entry of this.signers) {
      if (entry.pattern === '*' || matchPattern(entry.pattern, network)) {
        return entry.signer;
      }
    }
    return null;
  }

  async apply(requirements: PaymentRequirements[]): Promise<PaymentRequirements[]> {
    const affordable: PaymentRequirements[] = [];
    for (const req of requirements) {
      const signer = this.findSigner(req.network);
      if (!signer) {
        // No signer for this network — keep the requirement so mechanism
        // matching can still select it (balance check is best-effort).
        affordable.push(req);
        continue;
      }

      let balance: bigint;
      try {
        balance = await signer.checkBalance(req.asset, req.network);
      } catch {
        // Signer cannot query this network; keep the requirement.
        affordable.push(req);
        continue;
      }

      let needed = BigInt(req.amount);
      if (req.extra?.fee?.feeAmount) {
        needed += BigInt(req.extra.fee.feeAmount);
      }
      const decimals = getDecimals(req);
      const token = findByAddress(req.network, req.asset);
      const symbol = token?.symbol ?? req.asset.slice(0, 8);
      const divisor = 10 ** decimals;
      const hBalance = (Number(balance) / divisor).toFixed(decimals);
      const hNeeded = (Number(needed) / divisor).toFixed(decimals);
      if (balance >= needed) {
        console.log(
          `[x402] ${symbol} on ${req.network}: balance=${hBalance} >= needed=${hNeeded} (OK)`
        );
        affordable.push(req);
      } else {
        console.log(
          `[x402] ${symbol} on ${req.network}: balance=${hBalance} < needed=${hNeeded} (skipped)`
        );
      }
    }
    if (affordable.length === 0) {
      console.error('[x402] All payment requirements filtered: insufficient balance');
    }
    return affordable;
  }
}
