#!/bin/bash
# check-balance.sh - Check USDT balance on TRON for tvm-x402 payments
#
# Usage:
#   ./check-balance.sh <tron_address> [network]
#
# Networks: mainnet (default), nile

set -e

WALLET="${1:-}"
NETWORK="${2:-mainnet}"

if [ -z "$WALLET" ]; then
  echo "Usage: check-balance.sh <tron_address> [network]"
  echo "Networks: mainnet, nile"
  exit 1
fi

# USDT contract address on TRON (TRC20)
if [ "$NETWORK" = "mainnet" ]; then
  USDT_ADDRESS="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
  RPC="${TRON_RPC_URL:-https://api.trongrid.io}"
elif [ "$NETWORK" = "nile" ]; then
  USDT_ADDRESS="TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"
  RPC="${TRON_NILE_RPC_URL:-https://nile.trongrid.io}"
else
  echo "Error: Unknown network '$NETWORK'"
  exit 1
fi

# Query USDT balance using TronGrid API
RESULT=$(curl -s "${RPC}/v1/accounts/${WALLET}/tokens" | jq -r ".data[] | select(.tokenId == \"${USDT_ADDRESS}\") | .balance")

if [ -z "$RESULT" ] || [ "$RESULT" = "null" ]; then
  BALANCE_USDT="0.000000"
else
  # USDT on TRON has 6 decimals
  BALANCE_USDT=$(echo "scale=6; $RESULT / 1000000" | bc)
fi

echo "Wallet: $WALLET"
echo "Network: TRON $NETWORK"
echo "USDT Balance: $BALANCE_USDT USDT"
