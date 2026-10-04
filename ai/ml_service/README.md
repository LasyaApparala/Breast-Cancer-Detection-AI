# ML Service

FastAPI + Celery service — hosts the XGBoost + MLP ensemble classifier, temperature scaling calibration layer, TNM Rule Engine, imaging pipeline (EfficientNet-B4), and Celery workers for async classification tasks.

## Setup (native)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Start API
uvicorn main:app --host 0.0.0.0 --port 8001
# Start Celery worker (separate terminal)
celery -A tasks worker --loglevel=info -Q classification_tasks
```
