from pathlib import Path
from typing import Dict, Optional

from sqlalchemy.orm import Session

from .config import settings
from . import models
from .schemas import EvaluationResultCreate

# Reuse existing OMR logic
from omr_eval import evaluate_sheet, load_keys


class OMRProcessor:
    def __init__(self) -> None:
        # Load keys once and cache
        self.keyA, self.keyB = load_keys()

    def get_key(self, set_version: str):
        if str(set_version).upper().strip() == "A":
            return self.keyA
        return self.keyB

    def process_image(
        self,
        db: Session,
        image_path: Path,
        set_version: str,
        student_id: Optional[str] = None,
    ) -> models.EvaluationResult:
        key = self.get_key(set_version)
        result = evaluate_sheet(str(image_path), key)

        payload = EvaluationResultCreate(
            file_name=image_path.name,
            file_path=str(image_path),
            set_version=set_version.upper(),
            student_id=student_id,
            total_score=result["total"],
            subject_scores=result["subject_scores"],
        )

        entity = models.EvaluationResult(
            file_name=payload.file_name,
            file_path=payload.file_path,
            set_version=payload.set_version,
            student_id=payload.student_id,
            total_score=payload.total_score,
            subject_scores=payload.subject_scores,
        )
        db.add(entity)
        db.commit()
        db.refresh(entity)
        return entity


processor = OMRProcessor()


