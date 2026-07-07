from pydantic import BaseModel
from typing import List

from view.VaultImageDTO import VaultImageDTO


class VaultResponseDTO(BaseModel):
    page: int
    size: int
    total: int
    items: List[VaultImageDTO]