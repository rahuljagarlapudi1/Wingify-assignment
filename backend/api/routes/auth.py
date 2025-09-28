# api/routes/auth.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Form, HTTPException, Depends
from auth.security import get_password_hash, verify_password, create_access_token
from models.user import User, UserRole
from config.settings import settings

router = APIRouter()

@router.post("/register")
async def register_user(
    email: str = Form(...),
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
):
    existing = await User.find_one({"$or": [{"email": email}, {"username": username}]})
    if existing:
        raise HTTPException(400, "User with this email or username already exists")
    user = User(
        email=email,
        username=username,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        role=UserRole.USER,
    )
    await user.save()
    return {"message": "User registered successfully", "user_id": str(user.id)}

@router.post("/login")
async def login_user(
    username: str = Form(...),
    password: str = Form(...),
):
    user = await User.find_one({"username": username})
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(401, "Incorrect username or password")
    if not user.is_active:
        raise HTTPException(401, "Account is inactive")
    user.last_login = datetime.utcnow()
    await user.save()
    token = create_access_token(data={"sub": str(user.id)},
                                expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": str(user.id), "username": user.username, "full_name": user.full_name, "role": user.role},
    }
