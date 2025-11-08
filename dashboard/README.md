# Dashboard (Streamlit)

## Run
1. Create a Python venv and install dependencies:
    python -m venv .venv
    source .venv/bin/activate
    pip install -r dashboard/requirements.txt

2. Start your FastAPI POC:
    uvicorn app.main:app --reload


3. Run the Streamlit app:
    export BASE_URL=http://localhost:8000
    streamlit run dashboard/streamlit_app.py


4. Use the dashboard to inspect sessions and transcripts.
