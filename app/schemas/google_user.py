from pydantic import BaseModel

class GoogleUser(BaseModel):
    google_sub: str
    email: str
    username: str

    class Config:
        from_orm = True
