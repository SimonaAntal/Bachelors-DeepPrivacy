import base64
import binascii
from io import BytesIO
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, UploadFile, Depends, File, Form, HTTPException, Query
from starlette.requests import Request
from starlette.responses import StreamingResponse
from dependencies.auth import get_current_user
from dependencies.db import get_db
from services.vault_service import add_image, decrypt_image, remove_image, get_file_image, get_images_filter

router = APIRouter(prefix="/vault", tags=["Vault"])

@router.post("/images")
async def upload_image(
        request: Request,
        name: Annotated[str, Form(
            min_length=3,
            max_length=50,
            pattern=r"^[A-Za-z0-9 _.-]+$")],
        file: UploadFile=File(...),
        current_user=Depends(get_current_user),
        db=Depends(get_db)
):
    owner_id = current_user["user_id"]
    role = current_user["role"]

    if role != "USER":
        raise HTTPException(403,"Forbidden")

    if file.content_type not in ("image/png", "image/jpeg"):
        raise HTTPException(415, "Only PNG and JPG images are allowed")

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 10 * 1024 * 1024:
        raise HTTPException(413, "Maximum file size is 10 MB")

    return await add_image(db, owner_id, name, file)

@router.post("/images/{image_id}/recover")
async def recover_image(
        image_id: str,
        key: Annotated[str, Form(
            min_length=40,
            max_length=100,
            pattern=r"^[A-Za-z0-9+/]+={0,2}$")],
        current_user=Depends(get_current_user),
        db=Depends(get_db)
):
    owner_id = current_user["user_id"]
    role = current_user["role"]

    if role != "USER":
        raise HTTPException(403,"Forbidden")

    if not ObjectId.is_valid(image_id):
        raise HTTPException(422, "Invalid image id")

    try:
        key_decoded = base64.b64decode(key, validate=True)
        if len(key_decoded) != 32:
            raise ValueError("Invalid key length")
    except (binascii.Error, ValueError):
        raise HTTPException(422, "Invalid recovery key")

    recovered_buffer = await decrypt_image(db, owner_id, image_id, key)

    return StreamingResponse(
        BytesIO(recovered_buffer.tobytes()),
        media_type="image/png"
    )

@router.delete("/images/{image_id}")
async def delete_image(
        image_id: str,
        key: Annotated[str, Form(
            min_length=40,
            max_length=100,
            pattern=r"^[A-Za-z0-9+/]+={0,2}$")],
        current_user=Depends(get_current_user),
        db=Depends(get_db)
):
    owner_id = current_user["user_id"]
    role = current_user["role"]

    if role != "USER":
        raise HTTPException(403, "Forbidden")

    if not ObjectId.is_valid(image_id):
        raise HTTPException(422, "Invalid image id")

    try:
        key_decoded = base64.b64decode(key, validate=True)
        if len(key_decoded) != 32:
            raise ValueError("Invalid key length")
    except (binascii.Error, ValueError):
        raise HTTPException(422, "Invalid recovery key")

    return await remove_image(db, owner_id, image_id, key)

@router.get("/images")
async def get_images(
        page: int = Query(1, ge=1),
        size: int = Query(6, ge=1, le=50),
        title: Annotated[str | None, Query(
            max_length=50,
            pattern=r"^[A-Za-z0-9 _.-]+$"
        )] = None,
        current_user=Depends(get_current_user),
        db=Depends(get_db)
):
    owner_id = current_user["user_id"]
    role = current_user["role"]

    if role != "USER":
        raise HTTPException(403, "Forbidden")

    return await get_images_filter(db, owner_id, page, size, title)

@router.get("/images/{image_id}")
async def get_images(
        image_id: str,
        current_user=Depends(get_current_user),
        db=Depends(get_db)
):
    owner_id = current_user["user_id"]
    role = current_user["role"]

    if role != "USER":
        raise HTTPException(403, "Forbidden")

    if not ObjectId.is_valid(image_id):
        raise HTTPException(422, "Invalid image id")

    return await get_images_filter(db, owner_id, image_id)

@router.get("/images/{image_id}/file")
async def get_image_file(
        image_id: str,
        current_user=Depends(get_current_user),
        db=Depends(get_db)
):
    owner_id = current_user["user_id"]
    role = current_user["role"]

    if role != "USER":
        raise HTTPException(403, "Forbidden")

    if not ObjectId.is_valid(image_id):
        raise HTTPException(422, "Invalid image id")

    return await get_file_image(db, owner_id, image_id)