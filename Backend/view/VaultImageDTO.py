from datetime import datetime
from pydantic import BaseModel

class VaultImageDTO(BaseModel):
    image_id: str
    name: str
    file_size: int
    uploaded_at: datetime