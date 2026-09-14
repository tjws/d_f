import os

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
    allow_headers=["Content-Type", "Authorization"],
)
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
