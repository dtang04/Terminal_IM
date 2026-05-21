from pydantic import BaseModel

class Username(BaseModel):
    username: str
    userid: str