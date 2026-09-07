from pydantic import BaseModel
from typing import Optional
from entities.application import FinalDecision

class ReviewDecisionRequest(BaseModel):
    decision: FinalDecision
    reason: Optional[str] = None
