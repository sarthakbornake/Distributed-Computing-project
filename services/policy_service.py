from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Dynamic ABAC Policy Service")

# Static policy data used by the experimental prototype.
ROLE_PERMISSIONS = {
    "admin": {"/api/data", "/api/admin"},
    "analyst": {"/api/data"},
    "user": {"/api/data"},
    "guest": set(),
}

ALLOWED_COUNTRIES = {
    "admin": {"IN"},
    "analyst": {"IN"},
    "user": {"IN"},
    "guest": set(),
}

MIN_DEVICE_TRUST = {
    "admin": 0.70,
    "analyst": 0.70,
    "user": 0.60,
    "guest": 0.99,
}

WINDOW_START = 6   # 06:00
WINDOW_END = 22    # 22:00

class PolicyRequest(BaseModel):
    user_id: str
    role: str
    path: str
    method: str = "GET"
    country: str = "IN"
    device_trust: float = Field(default=0.95, ge=0.0, le=1.0)
    request_hour: Optional[int] = Field(default=None, ge=0, le=23)

@app.get("/health")
def health():
    return {"service": "policy", "status": "ok"}

@app.post("/evaluate")
def evaluate(req: PolicyRequest):
    hour = req.request_hour
    if hour is None:
        hour = datetime.now(timezone.utc).hour

    reasons = []

    permissions = ROLE_PERMISSIONS.get(req.role, set())
    if req.path not in permissions:
        reasons.append("role_or_resource_not_allowed")

    allowed_countries = ALLOWED_COUNTRIES.get(req.role, set())
    if req.country not in allowed_countries:
        reasons.append("country_not_allowed")

    if not (WINDOW_START <= hour < WINDOW_END):
        reasons.append("outside_allowed_time_window")

    min_trust = MIN_DEVICE_TRUST.get(req.role, 1.0)
    if req.device_trust < min_trust:
        reasons.append("device_trust_too_low")

    allow = len(reasons) == 0

    return {
        "allow": allow,
        "reasons": reasons,
        "attributes_evaluated": {
            "role": req.role,
            "path": req.path,
            "country": req.country,
            "device_trust": req.device_trust,
            "request_hour": hour,
        },
    }
