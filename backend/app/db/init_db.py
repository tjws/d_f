from app.db.base import Base
from app.db.session import engine

# 导入模型，让 SQLAlchemy 知道需要创建 Customer 表。
from app.models.customer import Customer


def init_db():
    """根据所有模型创建数据库表。"""

    Base.metadata.create_all(bind=engine)