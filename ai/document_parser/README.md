# Document Parser Service

FastAPI service — extracts structured Clinical Features from PDF, JPEG, PNG, TIFF documents using pdfplumber, pytesseract OCR, and BioBERT NER.

## Setup (native)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002
```
