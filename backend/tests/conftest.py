"""测试进程的独立数据库配置。

必须在测试模块导入 app.db.session 之前设置 DATABASE_URL，
这样 pytest 永远不会清空开发用的 backend/data/app.db。
"""

import base64
import os
import tempfile
from pathlib import Path


TEST_DIRECTORY = Path(tempfile.mkdtemp(prefix="k12_sales_assistant_tests_"))
TEST_DATABASE_PATH = TEST_DIRECTORY / "app.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"
os.environ.setdefault(
    "APP_ENCRYPTION_KEY",
    base64.urlsafe_b64encode(b"t" * 32).decode("ascii"),
)
# 测试默认验证真实 JWT 权限，不继承开发服务器可能设置的绕过开关。
os.environ.pop("APP_DEV_AUTH_BYPASS", None)
# 测试禁止访问外部模型；运行环境的默认 Provider 由应用配置为 Bailian。
os.environ["AI_PROVIDER"] = "mock"


def pytest_configure() -> None:
    """使用与生产一致的 Alembic 链条初始化隔离测试库。"""

    from alembic import command
    from alembic.config import Config

    backend_directory = Path(__file__).resolve().parents[1]
    repository_root = backend_directory.parent
    config = Config(str(repository_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_directory / "alembic"))
    command.upgrade(config, "head")
