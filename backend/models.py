from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.types import JSON
from .database import Base


def _json_type():
    # Use native JSON if available, fallback to TEXT for SQLite older dialects
    try:
        return JSON
    except Exception:
        return Text


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    set_version = Column(String(1), nullable=False)  # 'A' or 'B'
    student_id = Column(String(255), nullable=True)
    total_score = Column(Integer, nullable=False)
    subject_scores = Column(SQLiteJSON().with_variant(_json_type(), "sqlite"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class UploadAudit(Base):
    __tablename__ = "upload_audit"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    saved_path = Column(String(1024), nullable=False)
    set_version = Column(String(1), nullable=False)
    student_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="processed")
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


