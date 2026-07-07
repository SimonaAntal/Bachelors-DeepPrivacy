from fastapi import APIRouter, Depends, Response

from dependencies.auth import get_current_user
from dependencies.db import get_db
from services.auth_service import create_account, login
from view.RegisterDTO import RegisterDTO
from view.SignInDTO import SignInDTO

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register")
async def register(dto: RegisterDTO, db=Depends(get_db)):
    return await create_account(db, dto)

@router.post("/login")
async def signin(
        dto: SignInDTO,
        response: Response,
        db=Depends(get_db)
):
    token = await login(db, dto)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=3600
    )

    return {
        "message": "Login successful"
    }

@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return current_user

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="access_token"
    )

    return {
        "message": "Logout successful"
    }