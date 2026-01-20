import { useMemo } from 'react';
import { WalletProvider } from '@tronweb3/tronwallet-adapter-react-hooks';
import {
  WalletModalProvider,
} from '@tronweb3/tronwallet-adapter-react-ui';
import { TronLinkAdapter } from '@tronweb3/tronwallet-adapters';
import { WalletError } from '@tronweb3/tronwallet-abstract-adapter';
import '@tronweb3/tronwallet-adapter-react-ui/style.css';

import { PaymentDemo } from './components/PaymentDemo';

function App() {
  const adapters = useMemo(() => [new TronLinkAdapter()], []);

  const onError = (error: WalletError) => {
    console.error('Wallet error:', error);
  };

  return (
    <WalletProvider
      onError={onError}
      adapters={adapters}
      disableAutoConnectOnLoad={true}
    >
      <WalletModalProvider>
        <div className="min-h-screen bg-gray-50 py-12 px-4">
          <div className="max-w-2xl mx-auto">
            <header className="text-center mb-8">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                x402 Tron Payment Demo
              </h1>
              <p className="text-gray-600">
                Demonstrates the x402 protocol for HTTP payment on TRON network
              </p>
            </header>
            <PaymentDemo />
          </div>
        </div>
      </WalletModalProvider>
    </WalletProvider>
  );
}

export default App;
