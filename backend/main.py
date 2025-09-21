from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import pandas as pd

from .config import settings
from .database import SessionLocal, init_db
from . import models, schemas
from .omr_service import processor


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="OVO OMR Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/upload", response_model=schemas.UploadResponse)
async def upload_sheets(
    files: List[UploadFile] = File(...),
    set_version: str = Query(..., description="OMR set version: A or B"),
    student_ids: Optional[List[str]] = Query(None, description="Optional parallel list of student IDs"),
    db: Session = Depends(get_db),
):
    if set_version.upper() not in {"A", "B"}:
        raise HTTPException(status_code=400, detail="set_version must be 'A' or 'B'")

    saved_results: List[schemas.EvaluationResultRead] = []

    for idx, file in enumerate(files):
        if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")

        # Save to upload dir
        target_dir = settings.DATA_DIR / datetime.utcnow().strftime("%Y%m%d")
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / file.filename
        content = await file.read()
        out_path.write_bytes(content)

        # Optional student id matching index
        student_id = None
        if student_ids and idx < len(student_ids):
            student_id = student_ids[idx]

        entity = processor.process_image(db, out_path, set_version=set_version, student_id=student_id)
        saved_results.append(schemas.EvaluationResultRead.model_validate(entity))

    return schemas.UploadResponse(processed=len(saved_results), results=saved_results)


@app.get("/results", response_model=List[schemas.EvaluationResultRead])
def list_results(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.EvaluationResult)
        .order_by(models.EvaluationResult.created_at.desc())
        .limit(limit)
        .all()
    )
    return [schemas.EvaluationResultRead.model_validate(r) for r in rows]


@app.get("/metrics", response_model=schemas.MetricsSummary)
def get_metrics(db: Session = Depends(get_db)):
    rows = db.query(models.EvaluationResult).all()
    if not rows:
        return schemas.MetricsSummary(
            total_sheets=0,
            average_score=0.0,
            max_score=0,
            min_score=0,
            per_subject_average={},
            perfect_sheets=0,
        )

    df = pd.DataFrame(
        [
            {
                "total": r.total_score,
                **{k: v for k, v in r.subject_scores.items()},
            }
            for r in rows
        ]
    )

    per_subject_avg = {col: float(df[col].mean()) for col in df.columns if col != "total"}

    return schemas.MetricsSummary(
        total_sheets=len(rows),
        average_score=float(df["total"].mean()),
        max_score=int(df["total"].max()),
        min_score=int(df["total"].min()),
        per_subject_average=per_subject_avg,
        perfect_sheets=int((df["total"] == 100).sum()),
    )


@app.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    rows = db.query(models.EvaluationResult).order_by(models.EvaluationResult.created_at.desc()).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No results to export")

    df = pd.DataFrame(
        [
            {
                "id": r.id,
                "file_name": r.file_name,
                "set_version": r.set_version,
                "student_id": r.student_id,
                **{f"{k}": v for k, v in r.subject_scores.items()},
                "total": r.total_score,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    )

    stream = BytesIO()
    df.to_csv(stream, index=False)
    stream.seek(0)
    return StreamingResponse(stream, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=results.csv"})


