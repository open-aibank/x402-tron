# x402 TypeScript Client SDK

TypeScript Client SDK for x402 Payment Protocol.

## Package

- `@open-aibank/x402-tron` - Complete TypeScript SDK for x402 on TRON (includes client, HTTP adapter, mechanisms, and signers)

## Installation

```bash
# Install the package
npm install @open-aibank/x402-tron

# Peer dependency
npm install tronweb
```

## Quick Start

```typescript
import { 
  X402Client,
  X402FetchClient,
  UptoTronClientMechanism,
  TronClientSigner
} from '@open-aibank/x402-tron';

// 1. Create signer
const signer = TronClientSigner.fromPrivateKey('your_private_key');

// 2. Create X402Client and register mechanisms
const x402Client = new X402Client()
  .register('tron:*', new UptoTronClientMechanism(signer));

// 3. Create HTTP client with automatic 402 handling
const client = new X402FetchClient(x402Client);

// 4. Make requests - 402 payments handled automatically
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
