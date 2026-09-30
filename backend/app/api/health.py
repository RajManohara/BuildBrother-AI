import logging
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(prefix="/api/health", tags=["Health"])
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal["ok", "ready", "unavailable"]
    service: str = "buildbrother-api"
    database: Literal["connected", "unavailable"] | None = None


@router.get("", response_model=HealthResponse)
def liveness():
    """Process health is independent of database readiness."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def readiness(request: Request):
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Database readiness check failed")
        return JSONResponse(status_code=503, content=HealthResponse(
            status="unavailable", database="unavailable"
        ).model_dump())
    return HealthResponse(status="ready", database="connected")
