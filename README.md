# OVO – OMR Evaluation System (MVP)

This repository provides a complete MVP for an OMR evaluation pipeline with a web application.

Flow
- Students fill OMR sheets during exams.
- Sheets are digitized individually via mobile.
- Evaluator uploads files via the web application.
- System pipeline executes:
  - Detects sheet orientation
  - Rectifies perspective distortion
  - Identifies bubble grid & extracts responses
  - Classifies marked/unmarked bubbles
  - Matches with answer key (per sheet set version)
  - Calculates section-wise and total scores
- Results are stored in a database and exportable as CSV
- Evaluator dashboard displays summaries (per student, per subject, aggregate stats)

Tech Stack
- Backend: FastAPI + SQLAlchemy (SQLite by default)
- OMR: OpenCV + Numpy (logic in `omr_eval.py`)
- Frontend: Streamlit (`frontend_app.py`)
- Storage: SQLite (local dev), upgradeable to PostgreSQL

Project Structure
```
OVO/
  backend/
    __init__.py
    config.py
    database.py
    main.py
    models.py
    omr_service.py
    schemas.py
  frontend_app.py
  omr_eval.py
  app.py                 # older Streamlit prototype (kept)
  sheets/
    Keys/
      KeySetA.csv
      KeySetB.csv
    Set A/ *.jpg|*.jpeg|*.png
    Set B/ *.jpg|*.jpeg|*.png
  requirements.txt
```

Prerequisites
- Python 3.10+
- Windows PowerShell (or any shell)

Setup (Windows PowerShell)
```powershell
cd D:\PROGRAMMING\Hackathons\Code4EdTech\OVO
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
# Backend deps
pip install fastapi uvicorn sqlalchemy pydantic[email] python-multipart
```

Run Backend (FastAPI)
```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Run Frontend (Streamlit)
```powershell
streamlit run frontend_app.py
```

Configuration
- Environment variables (optional):
  - `DATABASE_URL`: e.g. `sqlite:///D:/PROGRAMMING/Hackathons/Code4EdTech/OVO/ovo.db`
  - `OVO_DATA_DIR`: upload directory (default `uploads/` under project)
  - `OVO_KEYS_DIR`, `OVO_KEY_SET_A`, `OVO_KEY_SET_B`: custom key locations
  - `OVO_ALLOWED_ORIGINS`: comma list for CORS (default allows local Streamlit)

Answer Keys
- CSVs must include columns: `Python`, `EDA`, `SQL`, `POWER BI`, `Statistics`.
- Files go in `sheets/Keys/KeySetA.csv` and `sheets/Keys/KeySetB.csv`.

Notes
- You can still run the original Streamlit prototype with `streamlit run app.py`.
- For PostgreSQL, set `DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname` and `pip install psycopg2-binary`.
