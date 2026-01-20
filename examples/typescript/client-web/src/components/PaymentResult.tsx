interface PaymentResultProps {
  status: 'success' | 'error';
  result?: unknown;
  error?: string;
  onReset: () => void;
}

export function PaymentResult({ status, result, error, onReset }: PaymentResultProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      {status === 'success' ? (
        <>
          <div className="flex items-center justify-center mb-4">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <svg
                className="w-6 h-6 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
          </div>
          <h2 className="text-xl font-bold text-gray-900 text-center mb-2">
            Payment Successful!
          </h2>
          <p className="text-gray-600 text-center mb-4">
            You have successfully accessed the protected resource.
          </p>
          <div className="bg-gray-50 rounded-lg p-4 mb-4">
            <p className="text-sm text-gray-600 mb-2">Response:</p>
            <pre className="text-sm text-gray-900 overflow-auto max-h-40">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        </>
      ) : (
        <>
          <div className="flex items-center justify-center mb-4">
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
              <svg
                className="w-6 h-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
          </div>
          <h2 className="text-xl font-bold text-gray-900 text-center mb-2">
            Payment Failed
          </h2>
          <p className="text-red-600 text-center mb-4">{error}</p>
        </>
      )}

      <button
        onClick={onReset}
        className="w-full bg-gray-200 text-gray-800 py-2 px-4 rounded-lg font-medium hover:bg-gray-300 transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}
