from pydantic import BaseModel, Field
from typing import Optional
from typing import List

class Subcategory(BaseModel):
    id: int
    name: str

class CategoryWithSubcategories(BaseModel):
    category: str
    subcategories: List[Subcategory]
