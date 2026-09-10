from fastapi import FastAPI
from app.api.customers import router as customers_router
app = FastAPI(
    title="擎天学智 K12 智能销售辅助系统",
    version="0.1.0",
)
# 将客户路由注册到主应用。
# 注册后，/customers 接口才会生效。
app.include_router(customers_router)

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