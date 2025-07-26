from pydantic import BaseModel, Field, EmailStr
from typing import Optional 


class VideoLinks(BaseModel):
   how_to_buy: str
   how_to_sell: str
   how_to_rent: str
    
class AppLinks(BaseModel):
    app_store: str
    play_store: str

class SocialLinks(BaseModel):
    facebook: str
    instagram: str
    youtube: str
    twitter: str
    linkedin: str

class SettingsSchema(BaseModel):
    email: EmailStr
    whatsapp: str
    videos: VideoLinks
    app_links: AppLinks
    social_links: SocialLinks
