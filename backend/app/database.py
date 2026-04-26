from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from app.config import get_settings


settings = get_settings()
client: AsyncIOMotorClient = None
db = None


async def connect_to_mongo():
    """连接到MongoDB数据库"""
    global client, db
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]
    
    # 创建索引
    await create_indexes()
    
    print(f"Connected to MongoDB: {settings.mongodb_url}")
    print(f"Database: {settings.database_name}")


async def close_mongo_connection():
    """关闭MongoDB连接"""
    global client
    if client:
        client.close()
        print("MongoDB connection closed")


async def create_indexes():
    """创建数据库索引"""
    global db
    
    # 话题索引
    await db.topics.create_index([("created_at", DESCENDING)])
    await db.topics.create_index([("category", ASCENDING)])
    await db.topics.create_index([("is_active", ASCENDING)])
    
    # 辩论索引
    await db.debates.create_index([("created_at", DESCENDING)])
    await db.debates.create_index([("topic_id", ASCENDING)])
    await db.debates.create_index([("stage", ASCENDING)])
    await db.debates.create_index([("is_active", ASCENDING)])
    
    # 消息索引
    await db.messages.create_index([("debate_id", ASCENDING)])
    await db.messages.create_index([("created_at", ASCENDING)])
    await db.messages.create_index([("message_type", ASCENDING)])
    
    # 投票索引
    await db.votes.create_index([("debate_id", ASCENDING)])
    await db.votes.create_index([("user_id", ASCENDING)])
    await db.votes.create_index([("created_at", DESCENDING)])
    
    # 模型统计索引
    await db.model_stats.create_index([("model_id", ASCENDING)], unique=True)
    await db.model_stats.create_index([("win_rate", DESCENDING)])
    await db.model_stats.create_index([("avg_overall_score", DESCENDING)])
    
    # 用户索引
    await db.users.create_index([("username", ASCENDING)], unique=True)
    await db.users.create_index([("email", ASCENDING)], unique=True, sparse=True)
    
    print("Database indexes created successfully")


def get_database():
    """获取数据库实例"""
    global db
    return db


def get_collection(collection_name: str):
    """获取指定集合"""
    global db
    return db[collection_name]
