from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.exceptions import ConflictException, NotFoundException, UnprocessableException
from app.core.logging import setup_logging
from app.core.logging.loggers import error_logger

from app.modules.health.controllers.health_controller import router as health_router
from app.modules.organizations.controllers.organization_controller import router as organization_router
from app.modules.knowledge_bases.controllers.knowledge_base_controller import router as knowledge_base_router
from app.modules.agents.controllers.agent_controller import router as agent_router

setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)


# ── Domain exception handlers ───────────────────────────────────────────────

@app.exception_handler(NotFoundException)
async def not_found_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)}
    )


@app.exception_handler(ConflictException)
async def conflict_handler(request: Request, exc: ConflictException):
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc)}
    )


@app.exception_handler(UnprocessableException)
async def unprocessable_handler(request: Request, exc: UnprocessableException):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)}
    )


# ── Database integrity handler (safety net for unhandled FK/unique errors) ──

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    orig = str(exc.orig).lower()

    if "foreign key" in orig or "foreignkeyviolation" in orig:
        return JSONResponse(
            status_code=404,
            content={"detail": "El recurso referenciado no existe"}
        )

    if "unique" in orig or "uniqueviolation" in orig:
        return JSONResponse(
            status_code=409,
            content={"detail": "Ya existe un registro con esos datos"}
        )

    error_logger.error(
        f"Unhandled IntegrityError on {request.method} {request.url.path}: {exc}",
        exc_info=True
    )
    return JSONResponse(
        status_code=400,
        content={"detail": "Error de integridad en la base de datos"}
    )


# ── Generic fallback (never expose internals) ────────────────────────────────

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    error_logger.error(
        f"Unhandled {type(exc).__name__} on {request.method} {request.url.path}: {exc}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"}
    )


# ── Routers ──────────────────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(organization_router)
app.include_router(knowledge_base_router)
app.include_router(agent_router)


@app.get("/")
async def root():
    return {
        "message": settings.APP_NAME,
        "environment": settings.ENVIRONMENT
    }
