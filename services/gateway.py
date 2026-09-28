import os
from pathlib import Path
from typing import Optional

import httpx
import jwt
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Distributed API Gateway")

PUBLIC_KEY_PATH = Path(
    os.getenv(
        "AUTH_PUBLIC_KEY_PATH",
        Path(__file__).resolve().parents[1] / "keys" / "public.pem",
    )
)
POLICY_URL = os.getenv("POLICY_URL", "http://127.0.0.1:8002")
RESOURCE_URL = os.getenv("RESOURCE_URL", "http://127.0.0.1:8003")

ALGORITHM = "RS256"
ISSUER = "mtech-distributed-computing"

ROLE_PERMISSIONS = {
    "admin": {"/api/data", "/api/admin"},
    "analyst": {"/api/data"},
    "user": {"/api/data"},
    "guest": set(),
}

def verify_token(authorization: Optional[str]):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")

    token = authorization.split(" ", 1)[1].strip()
    if not PUBLIC_KEY_PATH.exists():
        raise HTTPException(status_code=500, detail="Gateway public key not found")

    public_key = PUBLIC_KEY_PATH.read_text()

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    return claims

def static_rbac(claims, path: str):
    role = claims.get("role", "")
    allowed = path in ROLE_PERMISSIONS.get(role, set())
    if not allowed:
        return False, "static_rbac_denied"
    return True, "static_rbac_allowed"

async def forward_to_resource(path: str, method: str):
    url = RESOURCE_URL + path
    async with httpx.AsyncClient(timeout=10.0) as client:
        if method == "GET":
            resp = await client.get(url)
        else:
            resp = await client.post(url)
    return resp

@app.get("/health")
def health():
    return {"service": "gateway", "status": "ok"}

@app.api_route("/{full_path:path}", methods=["GET", "POST"])
async def gateway(
    full_path: str,
    request: Request,
    mode: str = "abac",
    authorization: Optional[str] = Header(default=None),
    x_geo_country: str = Header(default="IN"),
    x_device_trust: Optional[float] = Header(default=None),
    x_force_hour: Optional[int] = Header(default=None),
):
    path = "/" + full_path

    if mode not in {"noac", "rbac", "abac"}:
        raise HTTPException(status_code=400, detail="mode must be noac, rbac, or abac")

    # Baseline 1: direct routing
    if mode == "noac":
        resp = await forward_to_resource(path, request.method)
        return JSONResponse(
            status_code=resp.status_code,
            content=resp.json(),
            headers={"X-Auth-Mode": "noac"},
        )

    # RBAC and ABAC use stateless JWT verification.
    claims = verify_token(authorization)

    if mode == "rbac":
        allowed, reason = static_rbac(claims, path)
        if not allowed:
            return JSONResponse(
                status_code=403,
                content={"allow": False, "mode": "rbac", "reason": reason},
                headers={"X-Auth-Mode": "rbac"},
            )

        resp = await forward_to_resource(path, request.method)
        return JSONResponse(
            status_code=resp.status_code,
            content=resp.json(),
            headers={"X-Auth-Mode": "rbac"},
        )

    # Proposed: dynamic ABAC
    device_trust = (
        float(x_device_trust)
        if x_device_trust is not None
        else float(claims.get("device_trust", 0.0))
    )

    payload = {
        "user_id": claims.get("sub", ""),
        "role": claims.get("role", ""),
        "path": path,
        "method": request.method,
        "country": x_geo_country,
        "device_trust": device_trust,
        "request_hour": x_force_hour,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        policy_resp = await client.post(f"{POLICY_URL}/evaluate", json=payload)

    if policy_resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Policy service unavailable")

    decision = policy_resp.json()

    if not decision["allow"]:
        return JSONResponse(
            status_code=403,
            content={
                "allow": False,
                "mode": "abac",
                "reasons": decision["reasons"],
            },
            headers={"X-Auth-Mode": "abac"},
        )

    resp = await forward_to_resource(path, request.method)
    return JSONResponse(
        status_code=resp.status_code,
        content=resp.json(),
        headers={"X-Auth-Mode": "abac"},
    )
