from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.health import router
from app.core.config import Settings
from app.database import create_database
from app.api.workspace import router as workspace_router
from app.demo import seed
from app.security import RateLimiter


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        engine, sessions = create_database(config.database_url)
        application.state.engine = engine
        application.state.sessions = sessions
        application.state.settings = config
        try:
            if config.demo_mode:
                with sessions() as session:
                    seed(session)
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title="BuildBrother AI", version="0.2.0",
        description="Read-only GitHub investigation linked to deployment and runtime evidence.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware, allow_origins=config.cors_origins,
        allow_credentials=False, allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )
    limiter = RateLimiter()

    @application.middleware("http")
    async def guard(request, call_next):
        if request.method in ("POST", "PATCH", "PUT"):
            if not limiter.allow(request.client.host if request.client else "unknown"):
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers={"Retry-After": "60"})
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 1_048_576:
                    return JSONResponse({"detail": "Request body exceeds 1 MiB"}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request, error):
        return JSONResponse({"detail": "Database request failed; verify service health and migrations"}, status_code=503)

    application.include_router(router)
    application.include_router(workspace_router)
    return application


app = create_app()
