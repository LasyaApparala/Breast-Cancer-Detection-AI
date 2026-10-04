# BreastGuard AI — Complete Setup & Run Guide

## 🚀 Quick Start (5-10 minutes)

### Prerequisites
- Docker & Docker Compose installed
- Git
- 2GB free disk space
- 4GB+ RAM

### Step 1: Create Environment File

```bash
cd Breast-Cancer-Detection-AI
cp .env.example .env
```

### Step 2: Start All Services

```bash
docker-compose up -d
```

This will start:
- Frontend (React) — http://localhost:3000
- Backend API (FastAPI) — http://localhost:8000
- ML Service — http://localhost:8001
- Document Parser — http://localhost:8002
- RAG Service — http://localhost:8003
- PostgreSQL — localhost:5432 (optional)
- MongoDB — localhost:27017 (audit logs)
- Redis — localhost:6379 (task queue)

### Step 3: Verify Services Are Running

```bash
# Check all container status
docker-compose ps

# View logs for any service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs ml_service
```

### Step 4: Test Backend Health

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{"status": "ok", "service": "backend"}
```

### Step 5: Access the Application

- **Frontend Dashboard:** http://localhost:3000
- **API Documentation:** http://localhost:8000/docs
- **Swagger UI:** http://localhost:8000/redoc

---

## 🔧 Troubleshooting

### Port 8000 Already in Use

```bash
# Find process using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>

# Or change the port in docker-compose.yaml
```

### Services Not Starting

```bash
# View detailed logs
docker-compose logs -f

# Rebuild images
docker-compose down
docker-compose up --build -d
```

### Database Issues

```bash
# Reset database
rm backend/data/breastguard_dev.db*
docker-compose restart backend
```

### Memory Issues

```bash
# Increase Docker memory limit in Docker Desktop settings
# Or run with reduced services:
docker-compose up -d backend frontend postgres redis
```

---

## 📊 Database Initialization

On first startup, the backend automatically creates all database tables:

```python
# From backend/api/main.py (lifespan hook)
Base.metadata.create_all(bind=engine)
```

**Database Schema:**
- `sessions` — Classification sessions
- `documents` — Uploaded medical documents
- `classification_results` — AI predictions
- `audit_trail` — Feature provenance (HIPAA compliance)
- `override_log` — Physician overrides
- `model_versions` — ML model metadata

---

## 🧪 Test the Classification Workflow

### 1. Create a Test User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_clinician",
    "email": "test@example.com",
    "password": "TestPassword123!",
    "role": "clinician"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_clinician",
    "password": "TestPassword123!"
  }'
```

**Save the JWT token from the response.**

### 3. Upload a Document

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -F "file=@sample_medical_image.jpg"
```

### 4. Create Classification Session

```bash
curl -X POST http://localhost:8000/api/v1/classify \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "document_ids": ["<DOCUMENT_ID>"],
    "features": {
      "tumor_size_mm": {"value": 25, "source": "document"},
      "histological_grade": {"value": 2, "source": "document"},
      "margin_type": {"value": "circumscribed", "source": "document"}
    }
  }'
```

### 5. Check Classification Result

```bash
curl -X GET http://localhost:8000/api/v1/classify/<SESSION_ID>/review \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>"
```

---

## 📋 File Structure

```
Breast-Cancer-Detection-AI/
├── .env                          # ← Create from .env.example
├── docker-compose.yaml           # Service orchestration
├── Makefile                       # Convenience commands
│
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Environment validation
│   │   ├── db.py                # Database setup
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   │
│   │   ├── models/
│   │   │   ├── db_models.py     # SQLAlchemy ORM
│   │   │   └── mongodb_documents.py
│   │   │
│   │   ├── routers/
│   │   │   ├── classify.py      # Classification endpoints
│   │   │   ├── upload.py        # Document upload
│   │   │   ├── admin.py         # Admin endpoints
│   │   │   └── analysis.py
│   │   │
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── security/            # JWT authentication
│   │   ├── services/            # Business logic
│   │   ├── validation/          # Feature validation
│   │   └── utils/
│   │
│   └── data/
│       ├── breastguard_dev.db   # SQLite dev database
│       └── uploads/             # Uploaded files
│
├── ui/
│   └── frontend/
│       ├── src/
│       │   ├── App.tsx          # React entry point
│       │   ├── components/      # Reusable UI components
│       │   ├── pages/           # Page views
│       │   └── hooks/
│       │
│       ├── package.json
│       ├── vite.config.ts
│       ├── Dockerfile
│       └── tailwind.config.js
│
├── ai/
│   ├── ml_service/              # Classification & explainability
│   │   ├── main.py
│   │   ├── classifier.py        # Ensemble model
│   │   ├── severity_engine.py   # TNM staging
│   │   ├── explainability.py    # SHAP + Grad-CAM
│   │   └── Dockerfile
│   │
│   ├── document_parser/         # OCR & feature extraction
│   │   ├── main.py
│   │   ├── parser.py
│   │   ├── feature_extractor.py
│   │   ├── phi_deidentification.py
│   │   └── Dockerfile
│   │
│   └── rag_service/             # PubMed integration & RAG
│       ├── main.py
│       ├── pubmed_client.py
│       ├── embedding_service.py
│       ├── vector_store.py
│       └── Dockerfile
│
└── system-architecture.md        # Detailed architecture docs

```

---

## 🛑 Stop the Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# View running containers
docker-compose ps
```

---

## 🔍 API Endpoints

### Authentication
```
POST   /api/v1/auth/login          — User login
POST   /api/v1/auth/register       — User registration
```

### Classification
```
POST   /api/v1/classify            — Create session
GET    /api/v1/classify/{id}/review         — Review features
PATCH  /api/v1/classify/{id}/confirm        — Confirm & classify
POST   /api/v1/classify/{id}/override       — Override result
GET    /api/v1/classify/{id}/audit          — Get audit trail
GET    /api/v1/classify/{id}/export         — Export PDF report
```

### Documents
```
POST   /api/v1/upload              — Upload medical document
```

### Admin
```
GET    /api/v1/admin/statistics    — System stats
GET    /api/v1/admin/overrides/statistics    — Override stats
```

Full docs: http://localhost:8000/docs

---

## 🐛 Common Errors & Fixes

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'backend'` | Ensure working directory is project root; Docker handles this automatically |
| `Connection refused at localhost:8000` | Services haven't started; check `docker-compose logs` |
| `CORS error on frontend` | Update `ALLOWED_ORIGINS` in `.env` |
| `Database locked` | Remove `.db-shm` and `.db-wal` files; restart backend |
| `Out of memory` | Increase Docker memory limit to 4GB+ |

---

## 📚 Next Steps

1. **Explore API docs** → http://localhost:8000/docs
2. **Review architecture** → See `system-architecture.md`
3. **Test workflow** → Follow "Test the Classification Workflow" above
4. **Customize models** → Edit files in `ai/ml_service/`
5. **Deploy to production** → Use Kubernetes manifests in `backend/infra/`

---

## ✅ Success Indicators

When everything is running correctly:
- ✅ `docker-compose ps` shows all services as "Up"
- ✅ `curl http://localhost:8000/health` returns `{"status": "ok"}`
- ✅ Frontend loads at http://localhost:3000
- ✅ API docs available at http://localhost:8000/docs
- ✅ Database initialized with empty tables (ready for data)

---

**Need help?** Check the logs:
```bash
docker-compose logs -f --tail=100 backend
```

This will show real-time errors and help diagnose issues.
