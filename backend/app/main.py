from fastapi import FastAPI
from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.users import router as users_router
from app.api.organizations import router as organizations_router
from app.api.audit_logs import router as audit_logs_router
app = FastAPI(
    title="擎天学智 K12 智能销售辅助系统",
    version="0.1.0",
)
# 将客户路由注册到主应用。
# 注册后，/customers 接口才会生效。
app.include_router(customers_router)
# 注册用户相关接口。
app.include_router(auth_router)
# 用户管理接口。
app.include_router(users_router)
# 组织管理接口。
app.include_router(organizations_router)
# 审计日志只读查询接口。
app.include_router(audit_logs_router)

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
