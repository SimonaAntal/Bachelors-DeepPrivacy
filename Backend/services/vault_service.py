import base64
import os
import uuid
from datetime import datetime, timezone

import cv2
from fastapi import HTTPException
from starlette.responses import FileResponse

from exceptions.encrypt_exceptions import NoSensitiveRegionsException, EmbeddingException, DecryptionException
from model.image import Image
from repository.image_repository import save_image, find_by_owner_and_name, find_user_images, count_user_images, \
    find_image_by_id, delete_image_by_id
from services import encryption_service
from services.encryption_service import encrypt_image, delete_image_containers
from view.VaultImageDTO import VaultImageDTO
from view.VaultResponseDTO import VaultResponseDTO

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOAD_DIR = os.getenv("UPLOAD_DIR")

async def add_image(db, owner_id, name, file):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg"):
        raise HTTPException(415, "Only PNG and JPG images are allowed")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(413, "Maximum file size is 10 MB")

    if await find_by_owner_and_name(db, owner_id, name):
        raise HTTPException(409,"An image with this name already exists")

    extension = os.path.splitext(file.filename)[1]

    image_id = str(uuid.uuid4())
    stored_filename = f"{image_id}{extension}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)

    temp_path = f"temp_{uuid.uuid4()}.png"
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        encrypted_img, key = encrypt_image(temp_path)
        cv2.imwrite(file_path, cv2.cvtColor(
                encrypted_img,
                cv2.COLOR_RGB2BGR
            )
        )

        image_document = Image(
            owner_id=owner_id,
            name=name,
            file_path=file_path,
            file_size=os.path.getsize(file_path), # bytes
            uploaded_at=datetime.now(timezone.utc)
        )

        result = await save_image(db, image_document)

    except NoSensitiveRegionsException as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(422, str(e))
    except EmbeddingException as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(500,"Could not upload image")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {
        "image_id": str(result.inserted_id),
        "recovery_key": base64.b64encode(key).decode(),
        "message": "Image uploaded successfully"
    }


async def decrypt_image(db, owner_id, image_id, key):
    image = await find_image_by_id(db, image_id)
    if image is None:
        raise HTTPException(404, "Image not found")

    if image["owner_id"] != owner_id:
        raise HTTPException(403, "Forbidden")

    try:
        recovered = encryption_service.decrypt_image(image["file_path"], base64.b64decode(key))
    except FileNotFoundError:
        raise HTTPException(404, "Image file missing")
    except DecryptionException:
        raise HTTPException(422, "Invalid key or corrupted image")
    except Exception:
        raise HTTPException(500,"Could not decrypt image")

    return recovered

async def remove_image(db, owner_id, image_id, key):
    image = await find_image_by_id(db, image_id)
    if image is None:
        raise HTTPException(404, "Image not found")

    if image["owner_id"] != owner_id:
        raise HTTPException(403, "Forbidden")

    file_path = image["file_path"]
    try:
        deleted_containers = delete_image_containers(file_path, base64.b64decode(key))

        if os.path.exists(file_path):
            os.remove(file_path)
        await delete_image_by_id(db, image_id)

    except FileNotFoundError:
        raise HTTPException(404, "Image file missing")
    except DecryptionException:
        raise HTTPException(422, "Invalid key or corrupted image")
    except Exception:
        raise HTTPException(500, "Could not delete image")
    return {
        "message": "Image deleted successfully",
        "deleted_containers": deleted_containers
    }

async def get_images_filter(db, owner_id, page, size, title):
    skip = (page - 1) * size
    images = await find_user_images(db, owner_id, skip, size, title)
    total = await count_user_images(db, owner_id, title)

    items = [
        VaultImageDTO(
            image_id=str(img["_id"]),
            name=img["name"],
            file_size=img["file_size"],
            uploaded_at=img["uploaded_at"]
        )
        for img in images
    ]

    return VaultResponseDTO(
        page=page,
        size=size,
        total=total,
        items=items
    )

async def get_image(db, owner_id, image_id):
    image = await find_image_by_id(db, image_id)
    if image is None:
        raise HTTPException(404, "Image not found")

    if image["owner_id"] != owner_id:
        raise HTTPException(403, "Forbidden")

    return VaultImageDTO(
        image_id=str(image["_id"]),
        name=image["name"],
        file_size=image["file_size"],
        uploaded_at=image["uploaded_at"]
    )

async def get_file_image(db, owner_id, image_id):
    image = await find_image_by_id(db, image_id)
    if image is None:
        raise HTTPException(404, "Image not found")

    if image["owner_id"] != owner_id:
        raise HTTPException(403, "Forbidden")

    file_path = image["file_path"]

    if not os.path.exists(file_path):
        raise HTTPException(404, "Image file missing")

    return FileResponse(file_path)