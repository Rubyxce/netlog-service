from pydantic import BaseModel
from uuid import UUID

class LogItem(BaseModel):
    message_id: UUID
    device: str
    level: str
    message: str
    ts: str