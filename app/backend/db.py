# from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# engine = create_engine('sqlite:///ecommerce.db', echo=True)
engine = create_async_engine('postgresql+asyncpg://ecommerce:ecommerce@0.0.0.0:5433/ecommerce', echo=True)
# SessionLocal = sessionmaker(bind=engine)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass
