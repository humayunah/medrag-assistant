"""Tests for health and demo API endpoints."""

from jose import jwt

from app.core.config import settings


# ── Health endpoints ────────────────────────────────────────────────


class TestLiveness:
    def test_liveness_returns_200(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200

    def test_liveness_status_alive(self, client):
        data = client.get("/health/live").json()
        assert data["status"] == "alive"


class TestStartup:
    def test_startup_returns_200(self, client):
        resp = client.get("/health/startup")
        assert resp.status_code == 200

    def test_startup_contains_version(self, client):
        data = client.get("/health/startup").json()
        assert data["status"] == "started"
        assert "version" in data
        assert data["version"] == settings.APP_VERSION


class TestReadiness:
    def test_readiness_returns_200(self, client):
        resp = client.get("/health/ready")
        assert resp.status_code == 200

    def test_readiness_has_status(self, client):
        data = client.get("/health/ready").json()
        # Without a real DB the status will be "degraded" — that is acceptable
        assert data["status"] in ("ready", "degraded")

    def test_readiness_includes_checks(self, client):
        data = client.get("/health/ready").json()
        assert "checks" in data
        assert "database" in data["checks"]

    def test_readiness_includes_version(self, client):
        data = client.get("/health/ready").json()
        assert data["version"] == settings.APP_VERSION


# ── Demo session endpoint ───────────────────────────────────────────


class TestDemoSession:
    ENDPOINT = "/api/v1/demo/session"

    def test_demo_session_returns_200(self, client):
        resp = client.post(self.ENDPOINT)
        assert resp.status_code == 200

    def test_demo_session_response_shape(self, client):
        data = client.post(self.ENDPOINT).json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600

    def test_demo_session_token_is_valid_jwt(self, client):
        data = client.post(self.ENDPOINT).json()
        token = data["access_token"]

        decoded = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )

        assert decoded["sub"] == "00000000-0000-0000-0000-000000000001"
        assert decoded["aud"] == "authenticated"
        assert decoded["email"] == "demo@medrag.example"
        assert (
            decoded["app_metadata"]["tenant_id"]
            == "00000000-0000-0000-0000-000000000000"
        )
        assert decoded["app_metadata"]["role"] == "staff"
        assert decoded["app_metadata"]["is_demo"] is True

    def test_demo_session_contains_demo_tenant_id(self, client):
        data = client.post(self.ENDPOINT).json()
        assert data["demo_tenant_id"] == "00000000-0000-0000-0000-000000000000"
