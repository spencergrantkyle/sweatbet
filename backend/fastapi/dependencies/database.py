from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from backend.fastapi.core.init_settings import global_settings as settings

Base = declarative_base()

# Configure engine kwargs based on environment
_is_prod = getattr(settings, 'ENV_MODE', 'dev') == 'prod'

_sync_engine_kwargs = {}
_async_engine_kwargs = {"echo": False, "future": True}

if _is_prod:
    _sync_engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    })
    _async_engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    })

sync_engine = create_engine(settings.DB_URL, **_sync_engine_kwargs)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

async_engine = create_async_engine(settings.ASYNC_DB_URL, **_async_engine_kwargs)
AsyncSessionLocal = sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)


def init_db():
    import backend.fastapi.models  # noqa: F401
    if not _is_prod:
        Base.metadata.create_all(bind=sync_engine)


async def close_engines():
    """Dispose engine connections for graceful shutdown."""
    sync_engine.dispose()
    await async_engine.dispose()


def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
