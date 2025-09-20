$ErrorActionPreference = "Stop"

Write-Host "Setting up virtual environment..."
if (!(Test-Path .venv)) {
    python -m venv .venv
}

Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing dependencies..."
if (Test-Path requirements.txt) {
    pip install -r requirements.txt
} else {
    pip install streamlit opencv-python-headless numpy pandas pillow
}

Write-Host "Launching Streamlit app..."
streamlit run streamlit_app.py --server.runOnSave true


