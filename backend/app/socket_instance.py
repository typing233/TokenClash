import socketio

# 创建Socket.IO服务器实例（独立模块，避免循环导入）
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True
)
