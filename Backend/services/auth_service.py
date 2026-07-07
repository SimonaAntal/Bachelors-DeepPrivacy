from fastapi import HTTPException

from model.user import User
from repository.user_repository import find_by_username, find_by_email, save_user
from services.jwt_service import generate_token
from services.password_service import hash_password, verify_password


async def create_account(db, register_dto):
    if await find_by_username(db, register_dto.username):
        raise HTTPException(409, "Username already exists")

    if await find_by_email(db, register_dto.email):
        raise HTTPException(409, "Email is already registered")

    user = User(
        first_name=register_dto.first_name,
        last_name=register_dto.last_name,
        username=register_dto.username,
        email=register_dto.email,
        password_hash=hash_password(register_dto.password),
        role="USER"
    )

    await save_user(db, user)

    return {"message": "Account created"}


async def login(db, dto):
    user = await find_by_email(db, dto.email)

    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(dto.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    return generate_token(user["email"], user["role"])