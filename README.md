# Breast Tumor Severity Classifier

A clinical decision-support platform that accepts patient medical documents and structured clinical data, extracts oncology-validated features, and produces a grounded breast tumor severity classification. The two-step pipeline first determines benign vs. malignant, then applies TNM-based AJCC staging (Stage I–IV) for malignant cases only.

## Services and Ports

| Service         | Port |
|-----------------|------|
| Frontend        | 3000 |
| Backend API     | 8000 |
| ML Service      | 8001 |
| Document Parser | 8002 |
| PostgreSQL      | 5432 |
| Redis           | 6379 |

## Quick Start

```bash
cp .env.template .env
# Edit .env and fill in secrets (passwords, keys, etc.)
make up
```

## Deployment Methods

### Docker (recommended)

Requires Docker and Docker Compose. A single command starts all services:

```bash
make up
```

See `docker-compose.yml` for service definitions, build contexts, port mappings, and environment bindings.

### Native

Each service can be run directly on the host without Docker. See `README_NATIVE_SETUP.md` for per-service setup instructions using `pip` + virtualenv (Python services) and `npm` (frontend).

All services read configuration from a `.env` file in the project root or from the host shell environment.
