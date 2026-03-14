from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: dict  # {"code": "ERROR_CODE", "message": "Human-readable message"}
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str | None = None
    checks: dict | None = None
