from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import settings


# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},  # SQLite专用
)

# 创建异步Session工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# SQLAlchemy基类
class Base(DeclarativeBase):
    pass


async def get_db():
    """获取数据库会话(依赖注入)"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库(创建所有表 + 自动补列)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        from sqlalchemy import text, inspect
        def _migrate(sync_conn):
            insp = inspect(sync_conn)
            if "tasks" in insp.get_table_names():
                existing = {c["name"] for c in insp.get_columns("tasks")}
                if "pdf_info" not in existing:
                    sync_conn.execute(text("ALTER TABLE tasks ADD COLUMN pdf_info TEXT"))
        await conn.run_sync(_migrate)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
