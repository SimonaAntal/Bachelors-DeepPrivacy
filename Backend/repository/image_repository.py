from bson import ObjectId
from model.image import Image

async def find_by_owner_and_name(db, owner_id, name):
    return await db.images.find_one(
        {
            "owner_id": owner_id,
            "name": name
        }
    )

async def find_image_by_id(db, image_id):
    return await db.images.find_one(
        {
            "_id": ObjectId(image_id)
        }
    )

async def delete_image_by_id(db, image_id):
    await db.images.delete_one(
        {
            "_id": ObjectId(image_id)
        }
    )

async def save_image(db, img: Image):
    return await db.images.insert_one(img.model_dump())

async def count_user_images(db, owner_id, title=None):
    query = {
        "owner_id": owner_id
    }

    if title:
        query["name"] = {
            "$regex": title,
            "$options": "i"
        }

    return await db.images.count_documents(query)

async def find_user_images(db, owner_id, skip, limit, title=None):
    query = {
        "owner_id": owner_id
    }

    if title:
        query["name"] = {
            "$regex": title,
            "$options": "i"
        }

    cursor = (
        db.images
        .find(
            query,
            {
                "name": 1,
                "file_size": 1,
                "uploaded_at": 1
            }
        )
        .skip(skip)
        .limit(limit)
    )

    return await cursor.to_list(length=limit)