import { config } from 'dotenv';
import { resolve } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

import { TronWeb } from 'tronweb';

import { X402Client } from '@tvm-x402/core';
import { X402FetchClient } from '@tvm-x402/http-fetch';
import { UptoTronClientMechanism } from '@tvm-x402/mechanism-tron';
import { TronClientSigner } from '@tvm-x402/signer-tron';
import type { SettleResponse } from '@tvm-x402/core';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

config({ path: resolve(__dirname, '../../../../.env') });

const TRON_PRIVATE_KEY = process.env.TRON_PRIVATE_KEY || '';
const TRON_NETWORK = 'tron:nile';
const TRON_FULL_HOST = 'https://nile.trongrid.io';
const RESOURCE_SERVER_URL = 'http://localhost:8000';
const ENDPOINT_PATH = '/protected';
const RESOURCE_URL = RESOURCE_SERVER_URL + ENDPOINT_PATH;

if (!TRON_PRIVATE_KEY) {
  console.error('\n❌ Error: TRON_PRIVATE_KEY not set in .env file');
  console.error('\nPlease add your TRON private key to .env file\n');
  process.exit(1);
}

function decodePaymentResponse(encoded: string): SettleResponse | null {
  try {
    const jsonString = Buffer.from(encoded, 'base64').toString('utf8');
    return JSON.parse(jsonString) as SettleResponse;
  } catch {
    return null;
  }
}

function decodePaymentRequired(encoded: string): any | null {
  try {
    const jsonString = Buffer.from(encoded, 'base64').toString('utf8');
    return JSON.parse(jsonString);
  } catch {
    return null;
  }
}

async function main(): Promise<void> {
  console.log('Initializing X402 client...');
  console.log(`  Network: ${TRON_NETWORK}`);
  console.log(`  Resource: ${RESOURCE_URL}`);

  const tronWeb = new TronWeb({
    fullHost: TRON_FULL_HOST,
    privateKey: TRON_PRIVATE_KEY,
  }) as any;

  const signer = TronClientSigner.withPrivateKey(
    tronWeb,
    TRON_PRIVATE_KEY,
    'nile'
  );
  
  console.log(`  Client Address: ${signer.getAddress()}`);

  const x402Client = new X402Client().register(
    'tron:*',
    new UptoTronClientMechanism(signer)
  );

  const client = new X402FetchClient(x402Client);

  console.log(`\nRequesting: ${RESOURCE_URL}`);
  
  try {
    // Preflight once to capture requirements and print allowance before payment
    const preflight = await fetch(RESOURCE_URL);
    const paymentRequiredHeader = preflight.headers.get('payment-required');
    const paymentRequired = paymentRequiredHeader ? decodePaymentRequired(paymentRequiredHeader) : null;
    const accepted = paymentRequired?.accepts?.[0];
    const requiredToken = accepted?.asset as string | undefined;
    const payAmount = accepted?.amount ? BigInt(accepted.amount) : undefined;
    const feeAmount = accepted?.extra?.fee?.feeAmount ? BigInt(accepted.extra.fee.feeAmount) : BigInt(0);
    const requiredTotal = payAmount !== undefined ? payAmount + feeAmount : undefined;

    if (requiredToken && requiredTotal !== undefined) {
      const allowanceBefore = await signer.checkAllowance(requiredToken, requiredTotal, TRON_NETWORK);
      console.log(`\n[ALLOWANCE] Token: ${requiredToken}`);
      console.log(`[ALLOWANCE] Required total (payment + fee): ${requiredTotal.toString()}`);
      console.log(`[ALLOWANCE] Current allowance (before): ${allowanceBefore.toString()}`);
    } else {
      console.log('\n[ALLOWANCE] Unable to determine requirements from preflight response');
    }

    const response = await client.get(RESOURCE_URL);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} ${response.statusText}`);
    }

    console.log('\n✅ Request successful!');
    console.log(`Status: ${response.status}`);

    const paymentResponse = response.headers.get('payment-response');
    if (paymentResponse) {
      const settleResponse = decodePaymentResponse(paymentResponse);
      if (settleResponse) {
        console.log('\n📋 Payment settled:');
        console.log(`  Transaction: ${settleResponse.transaction}`);
        console.log(`  Network: ${settleResponse.network}`);
      }
    }

    if (requiredToken && requiredTotal !== undefined) {
      const allowanceAfter = await signer.checkAllowance(requiredToken, requiredTotal, TRON_NETWORK);
      console.log(`[ALLOWANCE] Current allowance (after): ${allowanceAfter.toString()}`);
    }
  } catch (error) {
    console.error('\n❌ Error:', error instanceof Error ? error.message : error);
    process.exit(1);
  }
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
