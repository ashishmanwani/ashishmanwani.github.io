import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import get_db
from api.deps import get_current_user
from api.models.user import User
from api.schemas.user import TelegramLinkRequest, TokenOut, UserLogin, UserOut, UserRegister
from api.services.auth_service import (
    create_access_token,
    generate_telegram_link_token,
    hash_password,
    verify_password,
)

router = APIRouter()


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/telegram/generate-link")
async def generate_telegram_link(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a magic token deep link for Telegram account linking."""
    from api.config import settings

    token = generate_telegram_link_token()
    current_user.telegram_link_token = token
    db.add(current_user)
    await db.commit()

    bot_name = "YourPriceTrackerBot"  # replace with actual bot username
    link = f"https://t.me/{bot_name}?start={token}"
    return {"telegram_link": link, "magic_token": token}


@router.post("/telegram/unlink")
async def unlink_telegram(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.telegram_chat_id = None
    current_user.telegram_link_token = None
    db.add(current_user)
    await db.commit()
    return {"message": "Telegram account unlinked"}
