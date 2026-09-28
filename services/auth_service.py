from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP = FastAPI(title="Authentication Service")

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_KEY_PATH = ROOT / "keys" / "private.pem"

ALGORITHM = "RS256"
ISSUER = "mtech-distributed-computing"

class TokenRequest(BaseModel):
    user_id: str = Field(min_length=1)
    role: str
    device_trust: float = Field(default=0.95, ge=0.0, le=1.0)

@APP.get("/health")
def health():
    return {"service": "auth", "status": "ok"}

@APP.post("/token")
def issue_token(req: TokenRequest):
    if not PRIVATE_KEY_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="RSA keys not found. Run scripts/generate_keys.py first."
        )

    now = datetime.now(timezone.utc)
    payload = {
        "sub": req.user_id,
        "role": req.role,
        "device_trust": req.device_trust,
        "iss": ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
    }

    private_key = PRIVATE_KEY_PATH.read_text()
    token = jwt.encode(payload, private_key, algorithm=ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_seconds": 1800,
    }

app = APP
