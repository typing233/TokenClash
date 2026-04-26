from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from bson import ObjectId
from app.database import get_database
from app.models.user import User, UserCreate, UserLogin, Token, TokenData
from app.config import get_settings


router = APIRouter()
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        is_admin: bool = payload.get("is_admin", False)
        
        if user_id is None:
            raise credentials_exception
        
        token_data = TokenData(
            user_id=user_id,
            username=username,
            is_admin=is_admin
        )
    except JWTError:
        raise credentials_exception
    
    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(token_data.user_id)})
    
    if user is None:
        raise credentials_exception
    
    return User(**user)


@router.post("/register", response_model=User)
async def register(user_data: UserCreate):
    """
    用户注册
    
    Args:
        user_data: 用户注册数据
    """
    db = get_database()
    
    # 检查用户名是否已存在
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # 检查邮箱是否已存在（如果提供）
    if user_data.email:
        existing_email = await db.users.find_one({"email": user_data.email})
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # 创建用户
    user_dict = {
        "username": user_data.username,
        "email": user_data.email,
        "display_name": user_data.display_name or user_data.username,
        "hashed_password": get_password_hash(user_data.password),
        "created_at": datetime.utcnow(),
        "last_login": None,
        "is_active": True,
        "is_admin": False,
        "total_votes": 0,
        "total_danmakus": 0,
        "watched_debates": []
    }
    
    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    
    return User(**user_dict)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    用户登录
    
    Args:
        form_data: 登录表单数据
    """
    db = get_database()
    
    # 查找用户
    user = await db.users.find_one({"username": form_data.username})
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # 更新最后登录时间
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": str(user["_id"]),
            "username": user["username"],
            "is_admin": user.get("is_admin", False)
        },
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.put("/me", response_model=User)
async def update_user_me(
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """更新当前用户信息"""
    db = get_database()
    
    update_data = {}
    if display_name:
        update_data["display_name"] = display_name
    if email:
        # 检查邮箱是否已被其他用户使用
        existing = await db.users.find_one({
            "email": email,
            "_id": {"$ne": current_user.id}
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        update_data["email"] = email
    
    if not update_data:
        return current_user
    
    await db.users.update_one(
        {"_id": current_user.id},
        {"$set": update_data}
    )
    
    # 获取更新后的用户
    updated_user = await db.users.find_one({"_id": current_user.id})
    return User(**updated_user)


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user)
):
    """修改密码"""
    db = get_database()
    
    # 获取用户的完整信息（包括hashed_password）
    user = await db.users.find_one({"_id": current_user.id})
    
    if not verify_password(old_password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect"
        )
    
    # 更新密码
    new_hashed_password = get_password_hash(new_password)
    await db.users.update_one(
        {"_id": current_user.id},
        {"$set": {"hashed_password": new_hashed_password}}
    )
    
    return {"message": "Password changed successfully"}


@router.get("/statistics")
async def get_user_statistics(current_user: User = Depends(get_current_user)):
    """获取用户统计数据"""
    db = get_database()
    
    # 获取用户的投票历史
    vote_count = await db.votes.count_documents({
        "user_id": str(current_user.id),
        "is_valid": True
    })
    
    # 获取用户的弹幕历史
    danmaku_count = await db.messages.count_documents({
        "user_id": str(current_user.id),
        "message_type": "danmaku"
    })
    
    return {
        "total_votes": vote_count,
        "total_danmakus": danmaku_count,
        "watched_debates_count": len(current_user.watched_debates) if current_user.watched_debates else 0
    }
