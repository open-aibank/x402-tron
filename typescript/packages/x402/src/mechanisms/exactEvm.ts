/**
 * ExactEvmClientMechanism - EVM client mechanism for "exact" payment scheme
 *
 * Uses EIP-712 for signing PaymentPermit. EVM addresses are used directly
 * without conversion.
 */

import type {
  ClientMechanism,
  ClientSigner,
  PaymentRequirements,
  PaymentPayload,
  PaymentPermit,
  PaymentPermitContext,
} from '../index.js';
import {
  KIND_MAP,
  PAYMENT_PERMIT_TYPES,
  getChainId,
  getPaymentPermitAddress,
  EVM_ZERO_ADDRESS,
  EvmAddressConverter,
  PermitValidationError,
} from '../index.js';

/**
 * EVM client mechanism for "exact" payment scheme
 */
export class ExactEvmClientMechanism implements ClientMechanism {
  private signer: ClientSigner;
  private addressConverter = new EvmAddressConverter();

  constructor(signer: ClientSigner) {
    this.signer = signer;
  }

  getSigner(): ClientSigner {
    return this.signer;
  }

  scheme(): string {
    return 'exact';
  }

  async createPaymentPayload(
    requirements: PaymentRequirements,
    resource: string,
    extensions?: { paymentPermitContext?: PaymentPermitContext }
  ): Promise<PaymentPayload> {
    const context = extensions?.paymentPermitContext;
    if (!context) {
      throw new PermitValidationError('missing_context', 'paymentPermitContext is required');
    }

    const buyerAddress = this.signer.getAddress();
    const zeroAddress = EVM_ZERO_ADDRESS;

    const permit: PaymentPermit = {
      meta: {
        kind: context.meta.kind,
        paymentId: context.meta.paymentId,
        nonce: context.meta.nonce,
        validAfter: context.meta.validAfter,
        validBefore: context.meta.validBefore,
      },
      buyer: buyerAddress,
      caller: context.caller || zeroAddress,
      payment: {
        payToken: requirements.asset,
        payAmount: requirements.amount,
        payTo: requirements.payTo,
      },
      fee: {
        feeTo: requirements.extra?.fee?.feeTo || zeroAddress,
        feeAmount: requirements.extra?.fee?.feeAmount || '0',
      },
    };

    // Ensure allowance
    const totalAmount = BigInt(permit.payment.payAmount) + BigInt(permit.fee.feeAmount);
    await this.signer.ensureAllowance(
      permit.payment.payToken,
      totalAmount,
      requirements.network
    );

    // Build EIP-712 domain (no version field per contract spec)
    const permitAddress = getPaymentPermitAddress(requirements.network);
    const domain = {
      name: 'PaymentPermit',
      chainId: getChainId(requirements.network),
      verifyingContract: this.addressConverter.toEvmFormat(permitAddress),
    };

    // Convert permit to EIP-712 compatible format
    // EVM addresses are already in 0x format, no conversion needed
    const permitForSigning = {
      meta: {
        kind: KIND_MAP[permit.meta.kind],
        paymentId: permit.meta.paymentId,
        nonce: BigInt(permit.meta.nonce),
        validAfter: permit.meta.validAfter,
        validBefore: permit.meta.validBefore,
      },
      buyer: permit.buyer,
      caller: permit.caller,
      payment: {
        payToken: permit.payment.payToken,
        payAmount: BigInt(permit.payment.payAmount),
        payTo: permit.payment.payTo,
      },
      fee: {
        feeTo: permit.fee.feeTo,
        feeAmount: BigInt(permit.fee.feeAmount),
      },
    };

    const signature = await this.signer.signTypedData(
      domain,
      PAYMENT_PERMIT_TYPES,
      permitForSigning as unknown as Record<string, unknown>
    );

    return {
      x402Version: 2,
      resource: { url: resource },
      accepted: requirements,
      payload: {
        signature,
        paymentPermit: permit,
      },
      extensions: {},
    };
  }
}
