"""
Facilitator Main Entry Point
Starts a FastAPI server for facilitator operations with full payment flow support.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add x402 to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "python" / "x402" / "src"))

from x402.logging_config import setup_logging
from x402.mechanisms.facilitator import UptoTronFacilitatorMechanism
from x402.signers.facilitator import TronFacilitatorSigner
from x402.types import (
    PaymentPayload,
    PaymentRequirements,
    VerifyResponse,
    SettleResponse,
    FeeQuoteResponse,
)

# Setup logging
setup_logging()

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

# Configuration
TRON_PRIVATE_KEY = os.getenv("TRON_PRIVATE_KEY", "")
TRON_NETWORK = os.getenv("TRON_NETWORK", "nile")
HOST = os.getenv("FACILITATOR_HOST", "0.0.0.0")
PORT = int(os.getenv("FACILITATOR_PORT", "8001"))
BASE_FEE = int(os.getenv("BASE_FEE", "1000000"))

if not TRON_PRIVATE_KEY:
    raise ValueError("TRON_PRIVATE_KEY environment variable is required")

# Initialize FastAPI app
app = FastAPI(
    title="X402 Facilitator",
    description="Facilitator service for X402 payment protocol",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize facilitator
facilitator_signer = TronFacilitatorSigner.from_private_key(
    TRON_PRIVATE_KEY,
    network=TRON_NETWORK,
)
facilitator_address = facilitator_signer.get_address()
facilitator_mechanism = UptoTronFacilitatorMechanism(
    facilitator_signer,
    fee_to=facilitator_address,
    base_fee=BASE_FEE,
)

print(f"Facilitator initialized:")
print(f"  Address: {facilitator_address}")
print(f"  Network: {TRON_NETWORK}")
print(f"  Base Fee: {BASE_FEE}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "X402 Facilitator",
        "status": "running",
        "facilitator_address": facilitator_address,
        "network": TRON_NETWORK,
        "base_fee": BASE_FEE,
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/fee-quote", response_model=FeeQuoteResponse)
async def fee_quote(requirements: PaymentRequirements):
    """
    Get fee quote for payment requirements
    
    Args:
        requirements: Payment requirements
        
    Returns:
        Fee quote response with fee details
    """
    try:
        result = await facilitator_mechanism.fee_quote(requirements)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verify", response_model=VerifyResponse)
async def verify(payload: PaymentPayload, requirements: PaymentRequirements):
    """
    Verify payment payload
    
    Args:
        payload: Payment payload with signature
        requirements: Payment requirements
        
    Returns:
        Verification result
    """
    try:
        result = await facilitator_mechanism.verify(payload, requirements)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/settle", response_model=SettleResponse)
async def settle(payload: PaymentPayload, requirements: PaymentRequirements):
    """
    Settle payment on-chain
    
    Args:
        payload: Payment payload with signature
        requirements: Payment requirements
        
    Returns:
        Settlement result with transaction hash
    """
    try:
        result = await facilitator_mechanism.settle(payload, requirements)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/payment-flow")
async def payment_flow(payload: PaymentPayload, requirements: PaymentRequirements):
    """
    Complete payment flow: verify + settle
    
    Args:
        payload: Payment payload with signature
        requirements: Payment requirements
        
    Returns:
        Complete flow result
    """
    try:
        # Step 1: Verify
        verify_result = await facilitator_mechanism.verify(payload, requirements)
        if not verify_result.is_valid:
            return {
                "success": False,
                "step": "verify",
                "error": verify_result.invalid_reason,
            }
        
        # Step 2: Settle
        settle_result = await facilitator_mechanism.settle(payload, requirements)
        
        return {
            "success": settle_result.success,
            "step": "settle",
            "transaction": settle_result.transaction if settle_result.success else None,
            "error": settle_result.error_reason if not settle_result.success else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Start the facilitator server"""
    print("\n" + "=" * 80)
    print("Starting X402 Facilitator Server")
    print("=" * 80)
    print(f"Host: {HOST}")
    print(f"Port: {PORT}")
    print(f"Facilitator Address: {facilitator_address}")
    print(f"Network: {TRON_NETWORK}")
    print("=" * 80)
    print("\nEndpoints:")
    print(f"  GET  http://{HOST}:{PORT}/")
    print(f"  GET  http://{HOST}:{PORT}/health")
    print(f"  POST http://{HOST}:{PORT}/fee-quote")
    print(f"  POST http://{HOST}:{PORT}/verify")
    print(f"  POST http://{HOST}:{PORT}/settle")
    print(f"  POST http://{HOST}:{PORT}/payment-flow")
    print("=" * 80 + "\n")
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
