# Backend Service

FastAPI backend — handles request routing, auth enforcement, orchestration of Document Parser and Severity Engine, async task dispatch, and result retrieval.

## Setup (native)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
