from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

# Debug: Print the URL to the console when the app starts
# (This helps verify the password is actually present)
print(f"CONNECTING TO: {settings.DATABASE_URL}")

engine = create_async_engine(
    settings.DATABASE_URL,  # Use the settings URL, NOT a hardcoded string
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    # REMOVED: connect_args={"server_settings": {"password": ""}} <- This was causing the error
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)