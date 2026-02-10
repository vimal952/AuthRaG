from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from bson import ObjectId
from database import get_db
from config import settings
from models.schemas import RegisterRequest, LoginRequest, TokenResponse
from utils.audit import log_event

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def create_token(user_id: str, email: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": user_id, "email": email, "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_admin(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest):
    db = get_db()
    existing = await db.users.find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_count = await db.users.count_documents({})
    role = "admin" if user_count == 0 else "user"

    result = await db.users.insert_one({
        "email": body.email,
        "name": body.name,
        "password": hash_password(body.password),
        "role": role,
        "created_at": datetime.utcnow(),
    })
    user_id = str(result.inserted_id)
    token = create_token(user_id, body.email, role)

    await log_event("register", user_id, body.email, role)
    return TokenResponse(
        access_token=token,
        user={"id": user_id, "email": body.email, "name": body.name, "role": role},
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    db = get_db()
    user = await db.users.find_one({"email": body.email})
    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(user["_id"])
    token = create_token(user_id, user["email"], user["role"])

    await log_event("login", user_id, user["email"], user["role"])
    return TokenResponse(
        access_token=token,
        user={"id": user_id, "email": user["email"], "name": user["name"], "role": user["role"]},
    )


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    }
