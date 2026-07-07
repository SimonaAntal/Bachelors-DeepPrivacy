from pydantic import BaseModel, EmailStr

class User(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    password_hash: str
    role: str = "USER"