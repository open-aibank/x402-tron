/**
 * Helpers for constructing agent-wallet providers without direct wallet imports.
 */

export interface TronProviderOptions {
  fullNode?: string;
  solidityNode?: string;
  eventServer?: string;
  privateKey?: string;
  apiKey?: string;
  keystore?: {
    path?: string;
    password?: string;
  };
}

export interface FlashProviderOptions extends TronProviderOptions {
  flashNode?: string;
  privyAppId?: string;
  privyAppSecret?: string;
  walletId?: string;
}

export async function createTronProvider(options: TronProviderOptions = {}): Promise<any> {
  // @ts-ignore agent-wallet is an optional dependency
  const { TronProvider } = await import('agent-wallet/wallet');
  return new TronProvider({
    ...options,
    keystore: options.keystore,
  });
}

export async function createFlashProvider(options: FlashProviderOptions = {}): Promise<any> {
  // @ts-ignore agent-wallet is an optional dependency
  const { FlashProvider } = await import('agent-wallet/wallet');
  const provider = new FlashProvider({
    ...options,
    keystore: options.keystore,
  });
  await provider.init();
  return provider;
}
