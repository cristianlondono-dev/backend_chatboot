from fastapi import APIRouter
from sqlalchemy import text

from app.core.database.session import engine

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)


@router.get("")
async def health_check():

    async with engine.connect() as connection:

        result = await connection.execute(
            text("SELECT 1")
        )

        value = result.scalar()

    return {
        "database": value == 1
    }