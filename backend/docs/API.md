# BreastGuard AI - API Documentation

## Overview

BreastGuard AI provides a comprehensive REST API for breast tumor severity assessment with medical document processing, AI analysis, and clinical decision support.

## Base URL

- **Development**: `http://localhost:8000/api/v1`
- **Production**: `https://api.breastguard.ai/api/v1`

## Authentication

### JWT Bearer Token Authentication

All API endpoints (except `/health` and `/auth/login`) require JWT authentication.

```http
Authorization: Bearer <jwt_token>
```

### Token Endpoints

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "clinician@hospital.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "user-uuid",
    "email": "clinician@hospital.com",
    "name": "Dr. Sarah Johnson",
    "role": "clinician",
    "department": "Oncology"
  }
}
```

#### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## Core Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "2.1.0",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "ml_service": "healthy",
    "document_parser": "healthy"
  }
}
```

### Analysis Endpoints

#### Create Analysis
```http
POST /analysis
Content-Type: multipart/form-data
Authorization: Bearer <token>

files: [File]
clinical_data: {
  "tumor_size": 2.5,
  "tumor_grade": 2,
  "er_status": "positive",
  "pr_status": "positive",
  "her2_status": "negative",
  "ki67_index": 15.0,
  "lymph_node_involvement": false,
  "distant_metastasis": false,
  "bi_rads_score": 4
}
```

**Response:**
```json
{
  "id": "analysis-uuid",
  "user_id": "user-uuid",
  "status": "pending",
  "created_at": "2024-01-01T12:00:00Z",
  "clinical_data": {
    "tumor_size": 2.5,
    "tumor_grade": 2,
    "er_status": "positive",
    "pr_status": "positive",
    "her2_status": "negative",
    "ki67_index": 15.0,
    "lymph_node_involvement": false,
    "distant_metastasis": false,
    "bi_rads_score": 4
  }
}
```

#### Get Analysis
```http
GET /analysis/{analysis_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "analysis-uuid",
  "user_id": "user-uuid",
  "clinical_data": { ... },
  "files": [
    {
      "id": "file-uuid",
      "name": "mammogram_1.dcm",
      "type": "dicom",
      "size": 2048576,
      "uploaded_at": "2024-01-01T12:00:00Z",
      "url": "https://storage.breastguard.ai/files/file-uuid"
    }
  ],
  "result": {
    "id": "result-uuid",
    "severity": "Moderate",
    "confidence": 0.87,
    "uncertainty": 0.12,
    "stage": "Stage II",
    "feature_contributions": [
      {
        "feature": "Tumor Size",
        "contribution": 12.5,
        "importance": "high"
      },
      {
        "feature": "ER Status",
        "contribution": -5.2,
        "importance": "medium"
      }
    ],
    "image_heatmap": "https://storage.breastguard.ai/heatmaps/heatmap-uuid.png",
    "audit_trail": {
      "timestamp": "2024-01-01T12:05:00Z",
      "model_version": "BreastGuard-AI-v2.1.0",
      "input_hash": "a1b2c3d4e5f6",
      "clinician_review_required": false
    }
  },
  "status": "completed",
  "created_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:05:00Z"
}
```

#### List Analyses
```http
GET /analysis?skip=0&limit=50&status=completed
Authorization: Bearer <token>
```

**Response:**
```json
{
  "analyses": [ ... ],
  "total": 150,
  "skip": 0,
  "limit": 50
}
```

#### Request Clinician Review
```http
POST /analysis/{analysis_id}/review
Authorization: Bearer <token>
Content-Type: application/json

{
  "notes": "Patient requires follow-up imaging",
  "priority": "high"
}
```

## Document Processing

### Upload Document
```http
POST /documents/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: File
analysis_id: "analysis-uuid"
document_type: "mammogram"
```

**Response:**
```json
{
  "document_id": "doc-uuid",
  "filename": "mammogram_1.dcm",
  "file_type": "dicom",
  "file_size": 2048576,
  "storage_url": "https://storage.breastguard.ai/documents/doc-uuid",
  "processing_status": "pending",
  "uploaded_at": "2024-01-01T12:00:00Z"
}
```

### Extract Clinical Data
```http
POST /documents/extract
Content-Type: application/json
Authorization: Bearer <token>

{
  "document_id": "doc-uuid",
  "extraction_options": {
    "include_phi": false,
    "extract_entities": true,
    "generate_summary": true
  }
}
```

**Response:**
```json
{
  "document_id": "doc-uuid",
  "extracted_data": {
    "tumor_size": 2.5,
    "tumor_grade": 2,
    "er_status": "positive",
    "pr_status": "positive",
    "her2_status": "negative",
    "ki67_index": 15.0,
    "lymph_nodes_positive": false,
    "bi_rads_score": 4
  },
  "entities": [
    {
      "text": "invasive ductal carcinoma",
      "label": "DIAGNOSIS",
      "confidence": 0.95,
      "start": 45,
      "end": 70
    }
  ],
  "summary": "Pathology report indicates invasive ductal carcinoma, ER positive, PR positive, HER2 negative with Ki-67 index of 15%.",
  "extraction_confidence": 0.92,
  "processing_time_ms": 1250
}
```

## ML Service Integration

### Predict
```http
POST /ml/predict
Content-Type: application/json
Authorization: Bearer <token>

{
  "images": ["https://storage.breastguard.ai/images/img-uuid"],
  "clinical_data": {
    "tumor_size": 2.5,
    "tumor_grade": 2,
    "er_status": "positive",
    "pr_status": "positive",
    "her2_status": "negative",
    "ki67_index": 15.0,
    "lymph_node_involvement": false,
    "distant_metastasis": false
  },
  "text_reports": ["Pathology shows invasive ductal carcinoma..."],
  "options": {
    "include_explanations": true,
    "include_heatmap": true,
    "uncertainty_quantification": true
  }
}
```

**Response:**
```json
{
  "prediction": {
    "id": "pred-uuid",
    "severity": "Moderate",
    "confidence": 0.87,
    "uncertainty": 0.12,
    "stage": "Stage II",
    "model_ensemble": {
      "image_model": {
        "prediction": "malignant",
        "confidence": 0.91,
        "model": "EfficientNet-B4"
      },
      "tabular_model": {
        "prediction": "malignant",
        "confidence": 0.85,
        "model": "XGBoost"
      },
      "text_model": {
        "prediction": "malignant",
        "confidence": 0.83,
        "model": "BioBERT"
      },
      "meta_learner": {
        "prediction": "malignant",
        "confidence": 0.87,
        "model": "Logistic Regression"
      }
    },
    "feature_contributions": [
      {
        "feature": "Tumor Size",
        "contribution": 12.5,
        "importance": "high",
        "shap_value": 0.125
      }
    ],
    "explanations": {
      "shap_plot_url": "https://storage.breastguard.ai/explanations/shap-uuid.png",
      "grad_cam_url": "https://storage.breastguard.ai/explanations/gradcam-uuid.png",
      "feature_importance": {
        "tumor_size": 0.25,
        "er_status": 0.15,
        "tumor_grade": 0.20
      }
    },
    "audit_trail": {
      "timestamp": "2024-01-01T12:05:00Z",
      "model_version": "BreastGuard-AI-v2.1.0",
      "input_hash": "a1b2c3d4e5f6",
      "clinician_review_required": false
    }
  },
  "processing_time_ms": 3200
}
```

## User Management

### Get Current User
```http
GET /users/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "user-uuid",
  "email": "clinician@hospital.com",
  "name": "Dr. Sarah Johnson",
  "role": "clinician",
  "department": "Oncology",
  "license_number": "MD123456",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T11:30:00Z",
  "email_verified": true,
  "two_factor_enabled": false
}
```

### Update User Profile
```http
PUT /users/me
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Dr. Sarah Johnson",
  "department": "Oncology",
  "license_number": "MD123456"
}
```

## Admin Endpoints

### Get System Health
```http
GET /admin/health
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "system_status": "healthy",
  "services": {
    "backend": {
      "status": "healthy",
      "uptime": 86400,
      "memory_usage": "45%",
      "cpu_usage": "12%"
    },
    "database": {
      "status": "healthy",
      "connections": 25,
      "query_time_avg_ms": 45
    },
    "ml_service": {
      "status": "healthy",
      "model_loaded": true,
      "gpu_usage": "78%"
    }
  },
  "metrics": {
    "total_analyses": 1250,
    "active_users": 45,
    "error_rate_24h": 0.02
  }
}
```

### Get Audit Logs
```http
GET /admin/audit?start_date=2024-01-01&end_date=2024-01-02&event_type=analysis_created
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "audit_logs": [
    {
      "id": "audit-uuid",
      "event_type": "analysis_created",
      "user_id": "user-uuid",
      "analysis_id": "analysis-uuid",
      "timestamp": "2024-01-01T12:00:00Z",
      "ip_address": "192.168.1.100",
      "user_agent": "BreastGuard-Client/2.1.0"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 50
}
```

## Error Responses

### Standard Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid clinical data provided",
    "details": {
      "field": "tumor_size",
      "issue": "Value must be between 0.1 and 20.0 cm"
    },
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req-uuid"
  }
}
```

### Common Error Codes

- `UNAUTHORIZED` (401): Invalid or missing authentication
- `FORBIDDEN` (403): Insufficient permissions
- `NOT_FOUND` (404): Resource not found
- `VALIDATION_ERROR` (400): Invalid request data
- `RATE_LIMITED` (429): Too many requests
- `INTERNAL_ERROR` (500): Server error
- `SERVICE_UNAVAILABLE` (503): ML service or dependencies down

## Rate Limiting

### Limits

- **Standard users**: 100 requests per hour
- **Clinicians**: 500 requests per hour
- **Admin users**: 1000 requests per hour

### Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1640995200
```

## Webhooks

### Analysis Completion

Configure webhook URL to receive notifications when analysis completes.

```http
POST /webhooks/analysis-completed
Content-Type: application/json
X-BreastGuard-Signature: <hmac_signature>

{
  "event": "analysis.completed",
  "analysis_id": "analysis-uuid",
  "user_id": "user-uuid",
  "status": "completed",
  "result": { ... },
  "timestamp": "2024-01-01T12:05:00Z"
}
```

### Webhook Security

Webhook requests include HMAC signature for verification:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)
```

## SDKs and Libraries

### Python SDK

```python
from breastguard_ai import BreastGuardClient

client = BreastGuardClient(
    api_url="https://api.breastguard.ai/api/v1",
    api_key="your-api-key"
)

# Create analysis
analysis = client.create_analysis(
    files=["mammogram.dcm"],
    clinical_data={
        "tumor_size": 2.5,
        "tumor_grade": 2,
        "er_status": "positive"
    }
)

# Get results
result = client.get_analysis(analysis.id)
print(f"Severity: {result.result.severity}")
```

### JavaScript SDK

```javascript
import { BreastGuardAI } from '@breastguard-ai/sdk';

const client = new BreastGuardAI({
  baseURL: 'https://api.breastguard.ai/api/v1',
  apiKey: 'your-api-key'
});

const analysis = await client.createAnalysis({
  files: [file],
  clinicalData: {
    tumorSize: 2.5,
    tumorGrade: 2,
    erStatus: 'positive'
  }
});

console.log('Analysis ID:', analysis.id);
```

## Testing

### Sandbox Environment

- **URL**: `https://sandbox-api.breastguard.ai/api/v1`
- **Purpose**: Development and testing
- **Data**: Mock/anonymized data only

### Test Data

Sample clinical data for testing:

```json
{
  "tumor_size": 2.1,
  "tumor_grade": 2,
  "er_status": "positive",
  "pr_status": "positive", 
  "her2_status": "negative",
  "ki67_index": 18.5,
  "lymph_node_involvement": false,
  "distant_metastasis": false,
  "bi_rads_score": 4
}
```

## Support

### API Status

- **Status Page**: https://status.breastguard.ai
- **Incident History**: https://status.breastguard.ai/history

### Contact

- **API Support**: api-support@breastguard.ai
- **Documentation**: https://docs.breastguard.ai
- **GitHub Issues**: https://github.com/breastguard-ai/api/issues
