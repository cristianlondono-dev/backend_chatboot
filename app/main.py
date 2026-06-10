from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging

from app.modules.health.controllers.health_controller import router as health_router
from app.modules.organizations.controllers.organization_controller import router as organization_router
from app.modules.knowledge_bases.controllers.knowledge_base_controller import router as knowledge_base_router
from app.modules.agents.controllers.agent_controller import router as agent_router

setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)

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