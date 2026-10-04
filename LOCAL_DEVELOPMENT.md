# BreastGuard AI — Local Development Setup (Without Docker)

## Prerequisites

Install on your system:
- Python 3.11+
- Node.js 18+
- PostgreSQL 13+ (or use SQLite - included)
- MongoDB 5+ (optional - for audit logs)
- Redis 6+ (optional - for task queue)

For quick local dev, you can skip PostgreSQL/MongoDB/Redis and use SQLite + in-memory alternatives.

---

## 🚀 Quick Setup (5 Steps)

### Step 1: Clone & Enter Repository

```bash
git clone https://github.com/LasyaApparala/Breast-Cancer-Detection-AI.git
cd Breast-Cancer-Detection-AI
```

### Step 2: Create Environment File

```bash
cp .env.example .env
```

Edit `.env` for local development:

```bash
# Use SQLite (no PostgreSQL needed)
DATABASE_URL=sqlite:///./backend/data/breastguard_dev.db

# Disable MongoDB/Redis (optional services)
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379

# Local service URLs
DOCUMENT_PARSER_URL=http://localhost:8002
ML_SERVICE_URL=http://localhost:8001
RAG_SERVICE_URL=http://localhost:8003

# Auth
JWT_SECRET_KEY=dev-secret-key-123
KMS_PROVIDER=local

# App
APP_ENV=development
```

### Step 3: Start Backend API

```bash
cd backend/api
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Database tables ready.
```

### Step 4: Start Frontend (New Terminal)

```bash
cd ui/frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

**Expected output:**
```
VITE v4.4.0 ready in XXX ms
➜  Local:   http://localhost:3000
```

### Step 5: Access the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health

---

## 🔧 Optional: Start ML Service Locally

If you want to test classification (requires PyTorch):

```bash
cd ai/ml_service
python -m venv venv

# Activate
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install
pip install -r requirements.txt

# Run
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## 🔧 Optional: Start Document Parser Locally

```bash
cd ai/document_parser
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

---

## 🔧 Optional: Start RAG Service Locally

```bash
cd ai/rag_service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

---

## 📋 Full Local Development Setup (All Services)

If you want everything running locally (recommended for development):

### Terminal 1 — Backend
```bash
cd backend/api
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2 — Frontend
```bash
cd ui/frontend
npm run dev
```

### Terminal 3 — ML Service (Optional)
```bash
cd ai/ml_service
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Terminal 4 — Document Parser (Optional)
```bash
cd ai/document_parser
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### Terminal 5 — RAG Service (Optional)
```bash
cd ai/rag_service
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

Then access:
- http://localhost:3000 (Frontend)
- http://localhost:8000/docs (API)

---

## 🗄️ Database Setup (Local)

### Option A: SQLite (Easiest - No Setup)
Already configured in `.env`:
```
DATABASE_URL=sqlite:///./backend/data/breastguard_dev.db
```

The database file is auto-created on first backend startup. No additional setup needed.

### Option B: PostgreSQL (Production-like)

Install PostgreSQL locally, then:

```bash
# Create database
createdb breastguard_ai

# Update .env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/breastguard_ai

# Run migrations (if using Alembic)
cd backend/api
alembic upgrade head
```

---

## 🧪 Test the API (Without Frontend)

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{"status": "ok", "service": "backend"}
```

### 2. Register User
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

### 3. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "password": "TestPass123!"
  }'
```

Save the `access_token` from response.

### 4. API with Token
```bash
curl http://localhost:8000/api/v1/admin/statistics \
  -H "Authorization: Bearer <YOUR_TOKEN>"
```

---

## 🐛 Troubleshooting Local Setup

### Python Module Not Found
```bash
# Ensure you're in the correct venv
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Port Already in Use
```bash
# Mac/Linux - Find & kill process
lsof -i :8000
kill -9 <PID>

# Windows - Find process
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Database Locked
```bash
# Remove SQLite lock files
rm backend/data/breastguard_dev.db-shm
rm backend/data/breastguard_dev.db-wal

# Restart backend
```

### Module Import Errors
```bash
# Ensure working directory is project root
cd /path/to/Breast-Cancer-Detection-AI

# Check Python path
echo $PYTHONPATH

# If needed, add project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Frontend Won't Connect to Backend
Update `.env` or frontend config to point to backend:
- Backend should be at: `http://localhost:8000`
- Check CORS in `.env`: `ALLOWED_ORIGINS=http://localhost:3000`

---

## 📦 Python Dependency Issues

If you get dependency conflicts, use a fresh venv:

```bash
# Remove old venv
rm -rf backend/api/venv

# Create new venv
cd backend/api
python3.11 -m venv venv
source venv/bin/activate

# Install with exact versions
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; print(fastapi.__version__)"
```

---

## 🎯 Minimal Setup (Just Backend + Frontend)

If you only want the UI + API (no ML/parsing/RAG):

```bash
# Terminal 1: Backend
cd backend/api && python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd ui/frontend
npm install
npm run dev
```

Then visit: http://localhost:3000

---

## 🚀 Next: Deploy with Docker

Once local development works, you can containerize:

```bash
docker-compose up --build -d
```

This uses the same `.env` file but runs services in containers instead of locally.

---

## ✅ Success Checklist

- ✅ Backend starts at http://localhost:8000
- ✅ Frontend loads at http://localhost:3000
- ✅ `/health` returns `{"status": "ok"}`
- ✅ API docs available at http://localhost:8000/docs
- ✅ Database initialized (check `backend/data/breastguard_dev.db`)

---

## 📚 File Locations

```
Breast-Cancer-Detection-AI/
├── .env                           ← Create this
├── backend/
│   └── api/
│       ├── main.py               ← FastAPI entry
│       ├── requirements.txt
│       └── data/
│           └── breastguard_dev.db ← SQLite database
│
├── ui/
│   └── frontend/
│       ├── package.json
│       ├── src/
│       └── vite.config.ts
│
└── ai/
    ├── ml_service/               ← Optional
    ├── document_parser/          ← Optional
    └── rag_service/              ← Optional
```

---

## 🛠️ Common Commands

```bash
# Start backend with auto-reload
cd backend/api && source venv/bin/activate
uvicorn main:app --reload

# Start frontend with HMR
cd ui/frontend && npm run dev

# View API docs
open http://localhost:8000/docs

# Test health
curl http://localhost:8000/health

# Reset database
rm backend/data/breastguard_dev.db*
# Restart backend to recreate

# Activate venv (Mac/Linux)
source venv/bin/activate

# Deactivate venv
deactivate

# Check Python version
python --version

# Install specific package
pip install package_name==1.2.3
```

---

**Ready to run locally? Start with Step 3 above!**
