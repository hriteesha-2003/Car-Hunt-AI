from pydantic import BaseModel, Field,HttpUrl
from typing import Optional
from fastapi import UploadFile


class HomeFeaturedItems(BaseModel):
    title: str
    image_File: str
    link:str

class UpdateHomeFeaturedItem(BaseModel):
    title: Optional[str] = None
    image_File: Optional[str] = UploadFile(None)
    link: Optional[str] = None