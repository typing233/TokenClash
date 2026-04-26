from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import connect_to_mongo, close_mongo_connection
from app.config import get_settings
from app.routes import topics, debates, votes, rankings, models, auth
from app.socket import setup_socket_events
from app.socket_instance import sio


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时连接数据库
    await connect_to_mongo()
    
    # 设置Socket.IO事件
    setup_socket_events(sio)
    
    yield
    
    # 关闭时断开数据库连接
    await close_mongo_connection()


# 创建FastAPI应用
app = FastAPI(
    title="TokenClash - AI辩论平台",
    description="社区驱动的AI实时辩论和评测应用",
    version="1.0.0",
    lifespan=lifespan
)


# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(topics.router, prefix="/api/topics", tags=["话题"])
app.include_router(debates.router, prefix="/api/debates", tags=["辩论"])
app.include_router(votes.router, prefix="/api/votes", tags=["投票"])
app.include_router(rankings.router, prefix="/api/rankings", tags=["排行榜"])
app.include_router(models.router, prefix="/api/models", tags=["模型配置"])
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])


# 健康检查端点
@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "app": "TokenClash",
        "version": "1.0.0"
    }


@app.get("/", tags=["系统"])
async def root():
    """根路径"""
    return {
        "message": "欢迎使用TokenClash AI辩论平台",
        "docs": "/docs",
        "version": "1.0.0"
    }


# 创建Socket.IO应用
socket_app = socketio.ASGIApp(sio, app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:socket_app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
