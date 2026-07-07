from model.user import User


async def find_by_email(db, email: str):
    return await db.users.find_one({"email": email})


async def find_by_username(db, username: str):
    return await db.users.find_one({"username": username})


async def save_user(db, user: User):
    return await db.users.insert_one(user.model_dump())