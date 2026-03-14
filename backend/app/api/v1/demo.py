from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Request
from jose import jwt

from app.core.config import settings
from app.middleware.rate_limit import check_rate_limit

logger = structlog.get_logger("demo_api")
router = APIRouter(prefix="/demo", tags=["Demo"])

# Fixed demo tenant/user IDs (must match seed_demo_data.py)
DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000000"
DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"


@router.post("/session")
async def create_demo_session(request: Request):
    """Generate a time-limited demo JWT (1 hour, read-only, scoped to demo tenant)."""
    # Rate limit: 5 sessions per hour per IP
    check_rate_limit(
        request,
        endpoint="demo_session",
        max_requests=settings.RATE_LIMIT_DEMO,
        window_seconds=3600,
        use_tenant=False,
    )

    # Generate JWT matching Supabase format
    now = datetime.now(timezone.utc)
    payload = {
        "sub": DEMO_USER_ID,
        "aud": "authenticated",
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "email": "demo@medrag.example",
        "app_metadata": {
            "tenant_id": DEMO_TENANT_ID,
            "role": "staff",
            "is_demo": True,
        },
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

    client_ip = request.client.host if request.client else "unknown"
    logger.info("demo_session_created", ip=client_ip)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 3600,
        "demo_tenant_id": DEMO_TENANT_ID,
    }
