from pydantic import BaseModel

class AboutUsSchema(BaseModel):
    description: str
