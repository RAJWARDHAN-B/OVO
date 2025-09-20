# Automated OMR Evaluation & Scoring System (MVP)

This project implements a scalable OMR evaluation pipeline and a Streamlit-based MVP for evaluators to upload OMR sheet images, compute subject-wise and total scores, review overlays, and export results.

## Key Features
- Image preprocessing: orientation detection and perspective rectification
- Bubble detection: contour-based extraction and adaptive thresholding
- Mark inference: per-row winner selection with ambiguity checks
- Answer key matching: multi-set support (A/B/...) from JSON or CSV
- Scoring: 5 subjects × 20 questions each, total out of 100
- Artifacts: saves rectified image, overlay, and JSON per sheet to `artifacts/<sheet_id>/`
- Web UI: Streamlit app for uploads, batch processing, review, and CSV export
- CLI: `batch_eval.py` to process a folder locally

## Project Structure
```
omr_eval.py          # Core OMR logic (preprocess, detect, evaluate, batch)
streamlit_app.py     # Streamlit MVP frontend
batch_eval.py        # CLI batch processor
run.ps1              # Windows setup + run script for Streamlit
requirements.txt     # Python dependencies
answer_key.json      # Example answer key (JSON) – replace with real data
sheets/              # Sample folders with images
```

## Getting Started (Windows)
1) Open PowerShell in the project directory
2) Run:
```
./run.ps1
```
This will create `.venv`, install dependencies, and launch the Streamlit app.

If PowerShell execution policy blocks the script, run in an elevated PowerShell:
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Using the Streamlit App
1) Load an answer key:
   - Default `answer_key.json` or `sheets/answer.csv`
   - Or upload your own JSON/CSV
2) Select the exam set (e.g., `A`, `B`)
3) Upload OMR images (JPG/PNG)
4) Click "Evaluate Uploaded Images"
5) Review rectified image and overlay per sheet
6) Download results CSV

Batch tab allows processing a local folder (e.g., `sheets/Set A`) and writes a CSV.

## Answer Key Format
Supported formats:

JSON:
```
{
  "A": ["B", "C", "D", "A", ... up to 100],
  "B": ["C", "A", ...]
}
```

CSV (wide): first row headers include `set`, `q1`..`q100`
```
set,q1,q2,...,q100
A,B,C,...,A
B,C,A,...,D
```

CSV (long):
```
set,question,answer
A,1,B
A,2,C
...
```

## CLI Batch Processing
```
python batch_eval.py "sheets/Set A" A answer_key.json --out results.csv
```

## Notes & Tuning
- The OMR detection thresholds are defined in `EvaluationConfig` (in `omr_eval.py`).
- For different sheet templates, you may need to tune area ratios, row grouping tolerance, and selection thresholds.
- For highly challenging images, consider augmenting with an ML mark-classifier.

## License
For internal use at Innomatics Research Labs; adapt as needed.
