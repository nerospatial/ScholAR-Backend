from typing import Literal, Union
from pydantic import BaseModel

class AckPayload(BaseModel):
    session_id: str
    path: str

class ErrorPayload(BaseModel):
    code: str
    message: str

class WSOut(BaseModel):
    """Outgoing WS envelope (we only send ack/error for this MVP)."""
    type: Literal["ack", "error"]
    v: int = 1
    data: Union[AckPayload, ErrorPayload]
