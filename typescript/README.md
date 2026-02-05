# x402 TypeScript Client SDK

TypeScript Client SDK for x402 Payment Protocol.

## Package

- `@open-aibank/x402-tron` - Complete TypeScript SDK with client, mechanisms, signers, and HTTP adapter

## Installation

```bash
# Install the package
pnpm add @open-aibank/x402-tron tronweb
```

## Quick Start

```typescript
import { X402Client, ExactTronClientMechanism, TronClientSigner, X402FetchClient } from '@open-aibank/x402-tron';
import TronWeb from 'tronweb';

// 1. Initialize TronWeb
const tronWeb = new TronWeb({
  fullHost: 'https://nile.trongrid.io',
  privateKey: 'your_private_key',
});

// 2. Create signer
const signer = TronClientSigner.withPrivateKey(tronWeb, 'your_private_key', 'nile');

// 3. Create X402Client and register mechanisms
const x402Client = new X402Client()
  .register('tron:*', new ExactTronClientMechanism(signer));

// 4. Create HTTP client with automatic 402 handling
const client = new X402FetchClient(x402Client);

// 5. Make requests - 402 payments handled automatically
const response = await client.get('https://api.example.com/premium-data');
console.log(await response.json());
```

## Development

```bash
# Install dependencies
pnpm install

# Build all packages
pnpm build

# Run tests
pnpm test
```

## License

MIT License
