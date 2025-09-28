from typing import List
from pydantic import BaseModel

# Base violation schema shared between request + compliance agent

class MissingItem(BaseModel):
    item: str

class Violation(BaseModel):
    person_id: int
    missing: List[MissingItem]

class ViolationMessage(BaseModel):
    frame_start: int
    frame_end: int
    state: str
    persons: int
    violations: List[Violation]


class EnrichedViolation(BaseModel):
    person_id: int
    missing: List[MissingItem]

class EnrichedMessage(BaseModel):
    frame_start: int
    frame_end: int
    state: str
    persons: int
    violations: List[EnrichedViolation]