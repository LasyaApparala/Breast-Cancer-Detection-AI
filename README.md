# BreastGuard AI - Clinical Decision Support Platform

A comprehensive AI-powered clinical decision support system for breast tumor severity assessment, built with React, FastAPI, PyTorch, and XGBoost.

## ⚡ Quick Links

- **System Architecture**: See [system-architecture.md](system-architecture.md) for detailed diagrams, data flow, and deployment architecture
- **API Documentation**: http://localhost:8000/docs (after running)
- **Live Dashboard**: http://localhost:3000 (after running)

## 🎯 Key Features

- **Secure Authentication** — JWT-based login with role-based access control (RBAC)
- **Multi-Modal AI** — Ensemble models combining image, clinical data, and text analysis
- **AI Explainability** — TreeSHAP and Grad-CAM for transparent decisions
- **Medical Literature** — Real-time PubMed integration via RAG
- **HIPAA Compliance** — PHI de-identification, audit logging, encrypted storage
- **Clinician Override** — Professional review workflow with full audit trails
- **Cancer Staging** — AJCC 8th edition TNM staging engine

## 🚀 Quick Start

### Prerequisites
- Docker (recommended) or Python 3.11+, Node.js 18+
- PostgreSQL 13+, MongoDB 5+, Redis 6+ (included in Docker Compose)

### Option 1: Docker (Recommended)
```bash
git clone <repository-url>
cd Breast-Cancer-Detection-AI

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Native Installation
```bash
# Backend
cd services/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# ML Service (new terminal)
cd services/ml_service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001

# Document Parser (new terminal)
cd services/document_parser
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002

# RAG Service (new terminal)
cd services/rag_service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8003

# Frontend (new terminal)
cd frontend
npm install && npm run dev
```

## 📋 Usage Workflow

1. **Sign Up** → Create account with medical credentials
2. **Upload** → Add medical images (DICOM, PDF, images)
3. **Review** → Verify extracted clinical features
4. **Analyze** → AI classification with TNM staging
5. **Review** → See confidence scores & feature contributions
6. **Override** → Optionally override diagnosis with audit logging

## 🏗️ Architecture Overview

```
Frontend (React)          →  Backend (FastAPI)  →  ML Service (PyTorch/XGBoost)
                               ↓
         PostgreSQL (Structured Data) + MongoDB (Audit Logs) + Redis (Cache/Queue)
                               ↓
         Document Parser (OCR/NLP) | RAG Service (PubMed)
```

**Detailed system architecture with diagrams**: See [system-architecture.md](system-architecture.md)

## 🔌 API Endpoints

### Authentication
- `POST /auth/login` — User login
- `POST /auth/register` — User registration

### Classification
- `POST /classify` — Create classification session
- `GET /classify/{session_id}/review` — Review extracted features
- `POST /classify/{session_id}/confirm` — Confirm and classify
- `POST /classify/{session_id}/override` — Physician override
- `GET /classify/{session_id}/audit` — Get audit trail

### Documents
- `POST /upload` — Upload medical documents

See full API docs at: http://localhost:8000/docs

## 📁 Project Structure

```
Breast-Cancer-Detection-AI/
├── frontend/                 # React 18 + TypeScript UI
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/           # Page components (Dashboard, Upload, Results)
│   │   └── App.tsx          # Entry point
│   └── package.json
├── services/
│   ├── backend/             # FastAPI backend (port 8000)
│   │   ├── routers/         # API endpoints
│   │   ├── models/          # Database ORM models
│   │   └── services/        # Business logic
│   ├── ml_service/          # ML inference (port 8001)
│   │   ├── classifier.py    # Ensemble model
│   │   ├── severity_engine.py
│   │   └── explainability.py
│   ├── document_parser/     # Document processing (port 8002)
│   │   ├── parser.py        # OCR + NLP
│   │   ├── feature_extractor.py
│   │   └── phi_deidentification.py
│   └── rag_service/         # Medical knowledge (port 8003)
│       ├── pubmed_client.py
│       └── vector_store.py
├── data/                    # Data storage
│   ├── database/            # PostgreSQL files
│   ├── chroma_db/          # Vector database
│   ├── models/             # ML weights
│   └── uploads/            # Document storage
├── docker-compose.yaml      # Service orchestration
└── system-architecture.md   # Detailed architecture docs
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Tailwind CSS, Zustand |
| **Backend** | FastAPI, Python, SQLAlchemy, Celery |
| **ML/AI** | PyTorch, EfficientNet-B4, XGBoost, BioBERT, SHAP |
| **Database** | PostgreSQL, MongoDB, Redis |
| **Document Processing** | Tesseract OCR, spaCy, PyDICOM, Presidio |
| **Infrastructure** | Docker, Docker Compose, Kubernetes-ready |
| **Monitoring** | Prometheus, Grafana |

## 🔐 Security & Compliance

- ✅ **HIPAA-style Compliance** — PHI de-identification, audit logging, encrypted storage
- ✅ **JWT Authentication** — Secure token-based auth (RS256)
- ✅ **Rate Limiting** — Protection against abuse
- ✅ **TLS 1.3** — Encrypted data in transit
- ✅ **Access Control** — Role-based permissions

## 🧪 Testing

```bash
# Backend tests
cd services/backend && pytest

# ML service tests
cd services/ml_service && pytest

# Frontend tests
cd frontend && npm test
```

## 📚 Documentation

- **System Architecture**: [system-architecture.md](system-architecture.md) — Detailed diagrams, data flows, deployment
- **API Reference**: http://localhost:8000/docs (OpenAPI/Swagger)
- **Backend Setup**: [services/backend/README.md](services/backend/README.md)
- **Infrastructure**: [backend/infra/README.md](backend/infra/README.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push to branch (`git push origin feature/your-feature`)
5. Open a Pull Request


## ⚠️ Medical Disclaimer

**BreastGuard AI is a decision support tool and should NOT be used as a replacement for professional medical judgment.** Always consult with qualified healthcare professionals before making clinical decisions.

## 🔒 Privacy Notice

This system processes protected health information (PHI) and is designed for HIPAA compliance. Ensure proper authorization and patient consent before processing any patient data.

---

**Need help?** Check [system-architecture.md](system-architecture.md) for detailed technical documentation, or review the inline code comments in the services.
