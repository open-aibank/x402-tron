import { useState, useCallback, useMemo } from 'react';
import { useWallet } from '@tronweb3/tronwallet-adapter-react-hooks';
import { WalletActionButton } from '@tronweb3/tronwallet-adapter-react-ui';
import type { PaymentRequired, PaymentRequirements } from '../types';
import { createPaymentPayload, encodePaymentPayload } from '../utils/payment';

interface PaymentCardProps {
  paymentRequired: PaymentRequired;
  serverUrl: string;
  endpoint: string;
  onSuccess: (result: unknown) => void;
  onError: (error: string) => void;
}

const NETWORK_NAMES: Record<string, string> = {
  'tron:mainnet': 'TRON Mainnet',
  'tron:shasta': 'TRON Shasta Testnet',
  'tron:nile': 'TRON Nile Testnet',
};

const TOKEN_NAMES: Record<string, string> = {
  'TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf': 'USDT',
  'TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8': 'USDC',
};

export function PaymentCard({
  paymentRequired,
  serverUrl,
  endpoint,
  onSuccess,
  onError,
}: PaymentCardProps) {
  const { address, connected, wallet } = useWallet();
  const [isPaying, setIsPaying] = useState(false);
  const [selectedRequirement, setSelectedRequirement] = useState<PaymentRequirements>(
    paymentRequired.accepts[0]
  );

  const networkName = useMemo(() => {
    return NETWORK_NAMES[selectedRequirement.network] || selectedRequirement.network;
  }, [selectedRequirement.network]);

  const tokenName = useMemo(() => {
    return TOKEN_NAMES[selectedRequirement.asset] || 'Token';
  }, [selectedRequirement.asset]);

  const formattedAmount = useMemo(() => {
    const amount = BigInt(selectedRequirement.amount);
    const decimals = 6; // USDT/USDC decimals
    const divisor = BigInt(10 ** decimals);
    const whole = amount / divisor;
    const fraction = amount % divisor;
    const fractionStr = fraction.toString().padStart(decimals, '0').replace(/0+$/, '');
    return fractionStr ? `${whole}.${fractionStr}` : whole.toString();
  }, [selectedRequirement.amount]);

  const handlePay = useCallback(async () => {
    if (!connected || !address || !wallet) {
      onError('Please connect your wallet first');
      return;
    }

    setIsPaying(true);

    try {
      // Get wallet adapter
      if (!wallet || !wallet.adapter) {
        throw new Error('Wallet adapter not available');
      }

      console.log('Creating payment payload with wallet adapter...');

      // Create payment payload
      const paymentPayload = await createPaymentPayload(
        selectedRequirement,
        paymentRequired.extensions,
        address,
        wallet
      );

      // Encode and send payment
      const encodedPayload = encodePaymentPayload(paymentPayload);
      const url = `${serverUrl}${endpoint}`;

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'PAYMENT-SIGNATURE': encodedPayload,
        },
      });

      if (response.ok) {
        const result = await response.json();
        onSuccess(result);
      } else {
        const errorText = await response.text();
        onError(`Payment failed: ${response.status} - ${errorText}`);
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Payment failed');
    } finally {
      setIsPaying(false);
    }
  }, [
    connected,
    address,
    wallet,
    selectedRequirement,
    paymentRequired.extensions,
    serverUrl,
    endpoint,
    onSuccess,
    onError,
  ]);

  return (
    <div className="p-6 bg-white rounded-xl shadow-sm">
      <h2 className="mb-4 text-2xl font-bold text-center text-gray-900">
        Payment Required
      </h2>

      <p className="mb-6 text-center text-gray-600">
        Access to protected content. To access this content, please pay{' '}
        <span className="font-semibold">${formattedAmount} {tokenName}</span>
      </p>

      {/* Faucet Link */}
      <p className="mb-6 text-sm text-center text-purple-600">
        Need {tokenName}?{' '}
        <a
          href="https://nileex.io/join/getJoinPage"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-purple-800"
        >
          Get some here.
        </a>
      </p>

      {/* Wallet Connection */}
      {!connected ? (
        <div className="space-y-4">
          <WalletActionButton className="px-4 py-3 w-full font-medium text-white bg-blue-600 rounded-lg transition-colors hover:bg-blue-700" />
        </div>
      ) : (
        <div className="space-y-4">
          {/* Disconnect Button */}
          <WalletActionButton className="px-4 py-3 w-full font-medium text-gray-800 bg-gray-200 rounded-lg transition-colors hover:bg-gray-300" />

          {/* Payment Details */}
          <div className="p-4 space-y-3 bg-gray-50 rounded-lg">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Wallet:</span>
              <span className="font-mono text-gray-900">
                {address?.slice(0, 6)}...{address?.slice(-4)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Amount:</span>
              <span className="font-medium text-gray-900">
                ${formattedAmount} {tokenName}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Network:</span>
              <span className="text-gray-900">{networkName}</span>
            </div>
          </div>

          {/* Pay Button */}
          <button
            onClick={handlePay}
            disabled={isPaying}
            className="px-4 py-3 w-full font-medium text-white bg-blue-600 rounded-lg transition-colors hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {isPaying ? 'Processing...' : 'Pay now'}
          </button>
        </div>
      )}

      {/* Payment Options (if multiple) */}
      {paymentRequired.accepts.length > 1 && (
        <div className="pt-4 mt-6 border-t border-gray-200">
          <p className="mb-2 text-sm text-gray-600">Payment options:</p>
          <div className="space-y-2">
            {paymentRequired.accepts.map((req, index) => (
              <button
                key={index}
                onClick={() => setSelectedRequirement(req)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm ${
                  selectedRequirement === req
                    ? 'bg-blue-100 border-blue-500 border'
                    : 'bg-gray-50 hover:bg-gray-100'
                }`}
              >
                {NETWORK_NAMES[req.network] || req.network} -{' '}
                {TOKEN_NAMES[req.asset] || 'Token'}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
