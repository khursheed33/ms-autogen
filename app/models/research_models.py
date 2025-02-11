from pydantic import BaseModel
from typing import Optional

class ResearchRequest(BaseModel):
    topic: str
    initial_context: Optional[str] = None

class HumanInput(BaseModel):
    session_id: str
    input: str