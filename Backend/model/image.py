from datetime import datetime
from pydantic import BaseModel

class Image(BaseModel):
    owner_id: str
    name: str
    file_path: str
    file_size: int
    uploaded_at: datetime