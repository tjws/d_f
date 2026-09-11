from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from collections.abc import Generator
from sqlalchemy.orm import Session
# 当前项目后端目录。
# session.py 位于 backend/app/db/ 下，所以 parents[2] 是 backend。
BACKEND_DIR = Path(__file__).resolve().parents[2]

# SQLite 数据库文件位置。
DATABASE_DIR = BACKEND_DIR / "data"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "app.db"


# SQLite 连接地址。
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


# 创建数据库引擎。
# check_same_thread=False 允许 FastAPI 在不同线程中使用 SQLite。
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """每次建立 SQLite 连接时启用外键约束。"""

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# 每次调用 SessionLocal() 都会创建一个数据库会话。
# 后续接口会通过会话查询、新增和修改数据。
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

def get_db() -> Generator[Session, None, None]:
    """为每次请求创建数据库会话，并在请求结束后关闭。"""

    db = SessionLocal()

    try:
        # yield 会把数据库会话交给当前接口使用。
        yield db
    finally:
        # 无论接口成功还是报错，最后都要关闭会话。
        db.close()