from fastapi import FastAPI

app = FastAPI(
    title="擎天学智 K12 智能销售辅助系统",
    version="0.1.0",
)


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