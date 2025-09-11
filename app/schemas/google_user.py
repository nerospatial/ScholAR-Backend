from pydantic import BaseModel

class GoogleUser(BaseModel):
    sub: str
    email: str
    name: str
