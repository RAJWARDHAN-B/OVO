from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class EvaluationResultCreate(BaseModel):
    file_name: str
    file_path: str
    set_version: str
    student_id: Optional[str] = None
    total_score: int
    subject_scores: Dict[str, int]


class EvaluationResultRead(BaseModel):
    id: int
    file_name: str
    file_path: str
    set_version: str
    student_id: Optional[str]
    total_score: int
    subject_scores: Dict[str, int]
    created_at: datetime

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    processed: int
    results: List[EvaluationResultRead]


class MetricsSummary(BaseModel):
    total_sheets: int
    average_score: float
    max_score: int
    min_score: int
    per_subject_average: Dict[str, float]
    perfect_sheets: int


