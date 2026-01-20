import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from x402.server import X402Server
from x402.fastapi import x402_protected
from x402.facilitator import FacilitatorClient
from x402.mechanisms.server import UptoTronServerMechanism

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

app = FastAPI(title="X402 Server", description="Protected resource server")

# Add CORS middleware to allow cross-origin requests from client-web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Configuration
TRON_NETWORK = "tron:nile"  # Hardcoded network
MERCHANT_CONTRACT_ADDRESS = os.getenv("MERCHANT_CONTRACT_ADDRESS", "")
USDT_TOKEN_ADDRESS = os.getenv("USDT_TOKEN_ADDRESS", "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf")
# Hardcoded server configuration
FACILITATOR_URL = "http://localhost:8001"
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

if not MERCHANT_CONTRACT_ADDRESS:
    raise ValueError("MERCHANT_CONTRACT_ADDRESS environment variable is required")

# Initialize server with mechanism and facilitator
server = X402Server()
# Register TRON mechanism
tron_mechanism = UptoTronServerMechanism()
server.register(TRON_NETWORK, tron_mechanism)
# Add facilitator
facilitator = FacilitatorClient(base_url=FACILITATOR_URL)
server.add_facilitator(facilitator)

print(f"Server Configuration:")
print(f"  Network: {TRON_NETWORK}")
print(f"  Merchant Contract: {MERCHANT_CONTRACT_ADDRESS}")
print(f"  USDT Token: {USDT_TOKEN_ADDRESS}")
print(f"  Facilitator URL: {FACILITATOR_URL}")

@app.get("/")
async def root():
    """Service info"""
    return {
        "service": "X402 Protected Resource Server",
        "status": "running",
        "network": TRON_NETWORK,
        "merchant_contract": MERCHANT_CONTRACT_ADDRESS,
        "facilitator": FACILITATOR_URL,
    }

@app.get("/protected")
@x402_protected(
    server=server,
    price="1 USDT",  # 1 USDT = 1000000 (6 decimals)
    network=TRON_NETWORK,
    pay_to=MERCHANT_CONTRACT_ADDRESS,
)
async def protected_endpoint(request: Request):
    return {"message": "Payment successful! Access granted.", "data": "Protected content"}

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 80)
    print("Starting X402 Protected Resource Server")
    print("=" * 80)
    print(f"Host: {SERVER_HOST}")
    print(f"Port: {SERVER_PORT}")
    print(f"Endpoint: http://{SERVER_HOST}:{SERVER_PORT}/protected")
    print("=" * 80 + "\n")
    
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
