import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.fastapi.dependencies.database import init_db, AsyncSessionLocal, close_engines
from backend.fastapi.crud.message import create_message_dict_async
from backend.data.init_data import models_data
from backend.fastapi.services.activity_scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database connection
    init_db()

    # Insert the initial data
    async with AsyncSessionLocal() as db:
        try:
            for raw_data in models_data:
                await create_message_dict_async(db, raw_data)
        finally:
            await db.close()

    # Start the background activity scheduler
    logger.info("Starting activity scheduler...")
    start_scheduler()

    yield

    # Shutdown: Dispose database connections
    await close_engines()

    # Shutdown: Stop the scheduler gracefully
    logger.info("Stopping activity scheduler...")
    stop_scheduler()