#!/usr/bin/env npx ts-node
/**
 * x402-fetch.ts - TVM-x402 payment-enabled fetch wrapper for TRON
 * 
 * Usage:
 *   npx ts-node x402-fetch.ts <url> [options]
 *   
 * Options:
 *   --method POST|GET|...
 *   --body '{"key":"value"}'
 *   --network mainnet|nile
 *   --dry-run  (show payment details without paying)
 * 
 * Environment:
 *   TRON_PRIVATE_KEY - Required for signing payments
 */

const TronWeb = require('tronweb');

const NETWORKS: Record<string, any> = {
  mainnet: {
    fullHost: process.env.TRON_RPC_URL || 'https://api.trongrid.io',
    name: 'TRON Mainnet',
  },
  nile: {
    fullHost: process.env.TRON_NILE_RPC_URL || 'https://nile.trongrid.io',
    name: 'TRON Nile Testnet',
  },
};

// USDT addresses per network (TRC20)
const USDT_ADDRESSES: Record<string, string> = {
  mainnet: 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t',
  nile: 'TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj',
};

interface PaymentRequirement {
  amount: string;
  currency: string;
  network: string;
  recipient: string;
  scheme: string;
  facilitator?: string;
}

async function parseArgs() {
  const args = process.argv.slice(2);
  const url = args[0];
  
  if (!url || url.startsWith('--')) {
    console.error('Usage: x402-fetch.ts <url> [--method POST] [--body "{}"] [--network mainnet|nile] [--dry-run]');
    process.exit(1);
  }

  const options: any = { url, method: 'GET', network: 'mainnet', dryRun: false };
  
  for (let i = 1; i < args.length; i++) {
    if (args[i] === '--method') options.method = args[++i];
    else if (args[i] === '--body') options.body = args[++i];
    else if (args[i] === '--network') options.network = args[++i];
    else if (args[i] === '--dry-run') options.dryRun = true;
  }

  return options;
}

function decodePaymentRequired(header: string): PaymentRequirement[] {
  try {
    const decoded = JSON.parse(Buffer.from(header, 'base64').toString('utf-8'));
    return Array.isArray(decoded) ? decoded : [decoded];
  } catch {
    throw new Error('Failed to decode PAYMENT-REQUIRED header');
  }
}

async function createPaymentSignature(
  requirement: PaymentRequirement,
  privateKey: string
): Promise<string> {
  const networkConfig = NETWORKS[requirement.network];
  if (!networkConfig) throw new Error(`Unsupported network: ${requirement.network}`);

  // Initialize TronWeb
  const tronWeb = new TronWeb({
    fullHost: networkConfig.fullHost,
    privateKey: privateKey,
  });

  const senderAddress = tronWeb.defaultAddress.base58;
  const usdtAddress = USDT_ADDRESSES[requirement.network];
  const nonce = Date.now();

  // Create TVM-x402 payment message for signing
  const message = {
    recipient: requirement.recipient,
    amount: requirement.amount,
    token: usdtAddress,
    nonce: nonce,
    network: requirement.network,
  };

  // Sign the message using TRON's signing mechanism
  const messageStr = JSON.stringify(message);
  const signature = await tronWeb.trx.sign(tronWeb.toHex(messageStr));

  // Create payment payload
  const payload = {
    signature,
    sender: senderAddress,
    nonce,
    network: requirement.network,
    scheme: requirement.scheme,
    message,
  };

  return Buffer.from(JSON.stringify(payload)).toString('base64');
}

async function x402Fetch(options: any) {
  const { url, method, body, network, dryRun } = options;
  
  console.log(`[tvm-x402] Requesting: ${method} ${url}`);

  // Step 1: Initial request
  const initialResponse = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body,
  });

  // If not 402, return response directly
  if (initialResponse.status !== 402) {
    console.log(`[tvm-x402] Response: ${initialResponse.status} (no payment required)`);
    return initialResponse;
  }

  // Step 2: Parse payment requirements
  const paymentHeader = initialResponse.headers.get('PAYMENT-REQUIRED');
  if (!paymentHeader) {
    throw new Error('402 response missing PAYMENT-REQUIRED header');
  }

  const requirements = decodePaymentRequired(paymentHeader);
  console.log('[tvm-x402] Payment required:');
  requirements.forEach((req, i) => {
    const amount = Number(req.amount) / 1e6; // USDT has 6 decimals
    console.log(`  [${i}] ${amount} ${req.currency} on ${req.network} → ${req.recipient.slice(0, 10)}...`);
  });

  if (dryRun) {
    console.log('[tvm-x402] Dry run - not paying');
    return initialResponse;
  }

  // Step 3: Select requirement matching preferred network
  const requirement = requirements.find(r => r.network === network) || requirements[0];
  console.log(`[tvm-x402] Selected: ${requirement.network}`);

  // Step 4: Create payment signature
  const privateKey = process.env.TRON_PRIVATE_KEY;
  if (!privateKey) {
    throw new Error('TRON_PRIVATE_KEY environment variable required');
  }

  console.log('[tvm-x402] Signing payment...');
  const paymentSignature = await createPaymentSignature(requirement, privateKey);

  // Step 5: Retry with payment
  console.log('[tvm-x402] Retrying with payment...');
  const paidResponse = await fetch(url, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      'PAYMENT-SIGNATURE': paymentSignature,
    },
    body,
  });

  console.log(`[tvm-x402] Response: ${paidResponse.status}`);
  
  if (paidResponse.status === 200) {
    const paymentResponse = paidResponse.headers.get('PAYMENT-RESPONSE');
    if (paymentResponse) {
      const settlement = JSON.parse(Buffer.from(paymentResponse, 'base64').toString());
      console.log(`[tvm-x402] Payment settled: ${settlement.txHash || 'confirmed'}`);
    }
  }

  return paidResponse;
}

// Main
(async () => {
  try {
    const options = await parseArgs();
    const response = await x402Fetch(options);
    
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const data = await response.json();
      console.log('\n--- Response ---');
      console.log(JSON.stringify(data, null, 2));
    } else {
      const text = await response.text();
      console.log('\n--- Response ---');
      console.log(text);
    }
  } catch (err: any) {
    console.error(`[tvm-x402] Error: ${err.message}`);
    process.exit(1);
  }
})();
