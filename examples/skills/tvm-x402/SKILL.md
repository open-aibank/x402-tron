---
name: tvm-x402
description: Use tvm-x402 protocol for HTTP-native crypto payments on TRON network. Use when Clawdbot needs to pay for APIs, access paid resources, or handle 402 Payment Required responses. Supports USDT payments on TRON via the tvm-x402 standard.
metadata: {"clawdbot":{"emoji":"💸","requires":{"anyBins":["node","npx"]},"env":["TRON_PRIVATE_KEY"]}}
---

# TVM-x402 Payment Protocol

TVM-x402 enables instant USDT payments on TRON directly over HTTP using the 402 Payment Required status code. Perfect for AI agents paying for APIs, data, or compute on-demand.

## Quick Start

### Install SDK
```bash
npm install tvm-x402
# or
pnpm add tvm-x402
```

### Environment Setup
```bash
# Store TRON wallet private key securely
export TRON_PRIVATE_KEY="your_tron_private_key"

# Optional: specify TRON network RPC
export TRON_RPC_URL="https://api.trongrid.io"
```

## How TVM-x402 Works

1. **Request** → Client calls a paid API
2. **402 Response** → Server returns payment details in `PAYMENT-REQUIRED` header
3. **Pay & Retry** → Client signs payment on TRON, retries with `PAYMENT-SIGNATURE` header
4. **Access** → Server verifies, settles on TRON, returns resource

## Using TVM-x402 Client

### TypeScript/Node.js
```typescript
import { x402Client } from 'tvm-x402';

const client = x402Client({
  privateKey: process.env.TRON_PRIVATE_KEY,
  network: 'tron',
});

// Automatic 402 handling
const response = await client.fetch('https://api.example.com/paid-endpoint');
const data = await response.json();
```

### With fetch wrapper
```typescript
import { wrapFetch } from 'tvm-x402';

const fetch402 = wrapFetch(fetch, {
  privateKey: process.env.TRON_PRIVATE_KEY,
  network: 'tron',
});

// Use like normal fetch - 402s handled automatically
const res = await fetch402('https://paid-api.com/data');
```

## Manual Flow (curl)

### Step 1: Discover payment requirements
```bash
curl -i https://api.example.com/paid-resource
# Returns 402 with PAYMENT-REQUIRED header (base64 JSON)
```

### Step 2: Decode payment details
```bash
# The PAYMENT-REQUIRED header contains base64-encoded JSON:
# {
#   "amount": "1000000",      # 1 USDT (6 decimals)
#   "currency": "USDT",
#   "network": "tron",
#   "recipient": "TXxx...",
#   "scheme": "exact"
# }
```

### Step 3: Sign and pay
```bash
# Use tvm-x402 CLI or SDK to create payment signature
npx ts-node scripts/x402-fetch.ts https://api.example.com/paid-resource \
  --network tron
```

### Step 4: Retry with proof
```bash
curl -H "PAYMENT-SIGNATURE: <base64_payload>" \
  https://api.example.com/paid-resource
```

## Common Patterns

### Pay for API calls
```typescript
// Weather API that costs 0.001 USDT per call
const weather = await client.fetch('https://weather-api.tvm-x402.org/forecast?city=NYC');
```

### Pay for AI inference
```typescript
// LLM API with per-token pricing
const completion = await client.fetch('https://llm.example.com/v1/chat', {
  method: 'POST',
  body: JSON.stringify({ prompt: 'Hello' }),
});
```

### Check balance before paying
```bash
# Check USDT balance on TRON
./scripts/check-balance.sh TYourAddress...
```

## Supported Networks

| Network | Chain ID | Status |
|---------|----------|--------|
| TRON Mainnet | - | ✅ Primary |
| TRON Nile Testnet | - | ✅ Supported |

## Payment Schemes

- **exact**: Pay fixed amount (e.g., 0.01 USDT per API call)
- **upto**: Pay up to max based on usage (e.g., LLM tokens)

## Error Handling

```typescript
try {
  const res = await client.fetch(url);
} catch (err) {
  if (err.code === 'INSUFFICIENT_BALANCE') {
    // Need to fund TRON wallet with USDT
  } else if (err.code === 'PAYMENT_FAILED') {
    // Transaction failed on TRON network
  } else if (err.code === 'INVALID_PAYMENT_REQUIREMENTS') {
    // Server sent malformed 402 response
  }
}
```

## Security Notes

- Never expose private keys in logs or chat
- Use environment variables for wallet credentials
- Prefer `op run` or similar for secret injection
- Review payment amounts before confirming large transactions

## Future Features

- **Wallet-based identity**: Skip repaying on every call with sessions
- **Auto-discovery**: APIs expose payment metadata at `/.well-known/tvm-x402`
- **Multi-facilitator**: Choose between payment processors on TRON

## Resources

- Spec: https://github.com/sun-protocol/tvm-x402
- Demo: See examples in this repository
