from pydantic import BaseModel, Field
from typing import Optional


class EvaluationCreate(BaseModel):
    target_type: str  # followup / inquiry / formal_order
    target_id: int
    subject_id: int
    score: int = Field(..., ge=1, le=10)
    comment: Optional[str] = None


class EvaluationOut(BaseModel):
    id: int
    evaluator_id: int
    evaluator_name: str
    subject_id: int
    subject_name: str
    target_type: str
    target_id: int
    score: int
    comment: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class EvaluationStatsPoint(BaseModel):
    date: str
    avg_score: float
    count: int


class EmployeeEvalStats(BaseModel):
    subject_id: int
    subject_name: str
    points: list[EvaluationStatsPoint]
