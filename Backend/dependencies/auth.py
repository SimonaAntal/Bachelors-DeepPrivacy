from fastapi import HTTPException, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.jwt_service import is_valid, extract_user_info

security = HTTPBearer()

async def get_current_user(
    access_token: str = Cookie(None)
):
    if access_token is None:
        raise HTTPException(401, "Missing token")

    if not is_valid(access_token):
        raise HTTPException(401,"Token expired or invalid")

    user_id, role = extract_user_info(access_token)
    if user_id is None:
        raise HTTPException(401,"Invalid token")

    return {
        "user_id": user_id,
        "role": role
    }