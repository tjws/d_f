import os
import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy import text
import redis

from fastapi import FastAPI
from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.users import router as users_router
from app.api.organizations import router as organizations_router
from app.api.audit_logs import router as audit_logs_router
from app.api.chat_messages import router as chat_messages_router
from app.api.wecom import router as wecom_router
from app.api.students import router as students_router
from app.api.timeline_events import router as timeline_events_router
from app.api.customer_profiles import router as customer_profiles_router
from app.api.ai_suggestions import router as ai_suggestions_router
from app.api.tags import router as tags_router
from app.api.schedules import router as schedules_router
from app.api.ai_workflow import router as ai_workflow_router
from app.api.ai_dashboard import router as ai_dashboard_router
from app.api.ai_workflow_admin import router as ai_workflow_admin_router
from app.api.knowledge import router as knowledge_router
from app.api.course_orders import router as course_orders_router
from app.api.service_tickets import router as service_tickets_router
from app.api.system_settings import router as system_settings_router
from app.api.system_status import router as system_status_router
from app.api.sales_scripts import router as sales_scripts_router
from app.api.agent import router as agent_router
from app.api.pending_actions import router as pending_actions_router
from app.api.my_work import router as my_work_router
from app.api.sidebar_sync import router as sidebar_sync_router
from app.api.ai_rollout import router as ai_rollout_router
from app.api.business_dashboard import router as business_dashboard_router
from app.api.admin_tags import router as admin_tags_router
from app.api.admin_operations import router as admin_operations_router
from app.api.admin_permissions import router as admin_permissions_router
from app.api.admin_data_export import router as admin_data_export_router
from app.api.admin_retention import router as admin_retention_router
from app.db.session import engine
from app.knowledge.qdrant_store import get_qdrant_client
from app.core.request_context import set_actor_user_id, set_request_id
from app.core.structured_logging import configure_json_logging

configure_json_logging()
request_logger = logging.getLogger("k12.request")
from app.core.dependencies import get_current_user, get_dev_user
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="擎天学智 K12 智能销售辅助系统",
    version="0.1.0",
)
# 仅允许本地 Vite 前端访问后端 API。
# 生产环境应替换为正式前端域名，不能直接使用 "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", "").strip()[:100] or str(uuid.uuid4())
        set_request_id(request_id)
        # 每个请求先清空操作者，避免线程复用时把上一个用户带入日志。
        set_actor_user_id(None)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_logger.info("http_request", extra={"event": "http_request", "method": request.method, "path": request.url.path, "status_code": status_code, "duration_ms": round((time.perf_counter() - started) * 1000, 2)})


app.add_middleware(RequestLoggingMiddleware)
# 将客户路由注册到主应用。
# 注册后，/customers 接口才会生效。
if (
    os.getenv("APP_ENV") == "development"
    and os.getenv("APP_DEV_AUTH_BYPASS") == "1"
):
    # 仅在本地开发环境显式开启时替换鉴权依赖，生产环境不会自动绕过 JWT。
    app.dependency_overrides[get_current_user] = get_dev_user

app.include_router(customers_router)
# 注册用户相关接口。
app.include_router(auth_router)
# 用户管理接口。
app.include_router(users_router)
# 组织管理接口。
app.include_router(organizations_router)
# 审计日志只读查询接口。
app.include_router(audit_logs_router)
# 本地 Mock 企业微信回调接口。
app.include_router(wecom_router)
app.include_router(students_router)
app.include_router(timeline_events_router)
app.include_router(chat_messages_router)
app.include_router(customer_profiles_router)
app.include_router(ai_suggestions_router)
app.include_router(tags_router)
app.include_router(schedules_router)
app.include_router(ai_workflow_router)
app.include_router(ai_dashboard_router)
app.include_router(ai_workflow_admin_router)
app.include_router(knowledge_router)
app.include_router(course_orders_router)
app.include_router(service_tickets_router)
app.include_router(system_settings_router)
app.include_router(system_status_router)
app.include_router(sales_scripts_router)
app.include_router(agent_router)
app.include_router(pending_actions_router)
app.include_router(my_work_router)
app.include_router(sidebar_sync_router)
app.include_router(ai_rollout_router)
app.include_router(business_dashboard_router)
app.include_router(admin_tags_router)
app.include_router(admin_operations_router)
app.include_router(admin_permissions_router)
app.include_router(admin_data_export_router)
app.include_router(admin_retention_router)

@app.get("/")
def read_root():
    return {
        "message": "K12 智能销售辅助系统后端已启动",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }


@app.get("/health/ready")
def readiness_check():
    """检查 API 依赖是否可用；不改变轻量 /health 的语义。"""
    checks: dict[str, str] = {}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
    try:
        client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6380/0"), socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        client.close()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
    # 启用向量检索时，Qdrant 也是运行必需依赖；关闭向量检索的本地单元测试不检查它。
    if os.getenv("RAG_VECTOR_ENABLED", "0").strip() == "1":
        try:
            get_qdrant_client().get_collections()
            checks["qdrant"] = "ok"
        except Exception:
            checks["qdrant"] = "error"
    if any(value != "ok" for value in checks.values()):
        return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})
    return {"status": "ready", "checks": checks}
