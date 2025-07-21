from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class Settings(BaseSettings):
    """应用级配置，默认值可被 .env 覆盖"""

    # PostgreSQL 连接参数
    db_host: str = "localhost"
    db_port: int = 5433
    db_user: str = "postgres"
    db_password: str = "147258"
    db_name: str = "collector"

    # SQLAlchemy
    echo_sql: bool = False  # True 时打印 SQL 调用，便于调试

    # 其他通用配置
    timezone: str = "Asia/Shanghai"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def db_uri(self) -> str:
        """SQLAlchemy 兼容的数据库 URI"""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:  # noqa: D401
    """懒加载 & 单例化 Settings 对象"""

    return Settings()


settings: Settings = get_settings()

# ---------------------------------------------------------------------------
# SQLAlchemy Engine / Session 工具
# ---------------------------------------------------------------------------

engine = create_engine(
    settings.db_uri,
    echo=settings.echo_sql,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """在应用启动时调用；自动建表。"""

    # 延迟导入，避免循环引用
    from app import models  # noqa: WPS433  # pylint: disable=C0415

    models.Base.metadata.create_all(bind=engine)  # type: ignore[attr-defined]


def get_db_session():
    """获取数据库会话"""
    return SessionLocal()
