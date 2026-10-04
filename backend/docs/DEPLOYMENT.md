# BreastGuard AI - Deployment Guide

## Overview

BreastGuard AI is a production-grade breast tumor severity assessment platform that combines multiple AI models with comprehensive security, monitoring, and compliance features.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend    │    │    Backend     │    │   ML Service   │
│   (React)     │◄──►│   (FastAPI)    │◄──►│ (PyTorch/XGBoost)│
│   Port: 3000   │    │   Port: 8000   │    │   Port: 8001   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Traefik      │    │   PostgreSQL   │    │     Redis       │
│  (Load Balancer)│    │ (Structured    │    │   (Task Queue)  │
│   Ports: 80/443│    │     Data)     │    │   Port: 6379   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                     ┌─────────────────┐
                     │    MongoDB     │
                     │  (Documents)   │
                     │ Port: 27017   │
                     └─────────────────┘
```

## Prerequisites

### System Requirements

- **CPU**: 8+ cores recommended for production
- **Memory**: 32GB+ RAM recommended
- **Storage**: 500GB+ SSD storage
- **GPU**: NVIDIA GPU with CUDA support (optional but recommended)
- **OS**: Linux (Ubuntu 20.04+ recommended)

### Software Dependencies

- Docker 20.10+
- Docker Compose 2.0+
- Git 2.30+
- OpenSSL (for SSL certificates)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/breastguard-ai.git
cd breastguard-ai
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Critical Environment Variables:**

```bash
# Security
JWT_PRIVATE_KEY_PATH=./keys/private.pem
JWT_PUBLIC_KEY_PATH=./keys/public.pem

# Database
POSTGRES_DB=breastguard_ai
POSTGRES_USER=breastguard_user
POSTGRES_PASSWORD=your_secure_password

# Storage
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_S3_BUCKET=breastguard-ai-storage
```

### 3. Generate SSL Certificates

```bash
# Create keys directory
mkdir -p keys

# Generate RSA keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# Generate SSL certificates (for production)
mkdir -p ssl
openssl req -x509 -newkey rsa:2048 -keyout ssl/key.pem -out ssl/cert.pem -days 365
```

### 4. Deploy with Docker Compose

**Development:**

```bash
docker-compose up -d
```

**Production:**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 5. Initialize Database

```bash
# Run database migrations
docker-compose exec backend alembic upgrade head

# Create admin user
docker-compose exec backend python -c "
from backend.security.auth import hash_password
from backend.models.user import User
from backend.db import SessionLocal

db = SessionLocal()
admin_user = User(
    email='admin@breastguard.ai',
    name='System Administrator',
    role='admin',
    password_hash=hash_password('your_admin_password')
)
db.add(admin_user)
db.commit()
print('Admin user created')
"
```

### 6. Verify Deployment

```bash
# Check service health
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health

# Check frontend
open http://localhost:3000
```

## Configuration Details

### Database Configuration

**PostgreSQL (Structured Data):**
- User sessions, analysis results, audit logs
- Optimized for ACID compliance and complex queries

**MongoDB (Documents):**
- Medical documents, PHI access logs, system metrics
- Optimized for document storage and retrieval

### Security Configuration

**JWT Authentication:**
- RS256 asymmetric encryption
- Access tokens: 30 minutes
- Refresh tokens: 7 days

**PHI Protection:**
- Automatic de-identification of PHI
- HIPAA-compliant audit logging
- Data retention policies

### ML Model Configuration

**Model Versions:**
- EfficientNet-B4 for image analysis
- XGBoost for clinical data
- BioBERT for text processing
- Ensemble meta-learner for fusion

**Explainability:**
- SHAP for feature importance
- Grad-CAM for image explanations
- Uncertainty quantification

## Production Deployment

### 1. Infrastructure Setup

**AWS EC2 Example:**

```bash
# Create EC2 instance
aws ec2 run-instances \
  --image-id ami-0abcdef123456789 \
  --instance-type m5.2xlarge \
  --key-name breastguard-key \
  --security-group-ids sg-12345678 \
  --subnet-id subnet-12345678 \
  --user-data file://user-data.sh
```

**User Data Script (user-data.sh):**

```bash
#!/bin/bash
apt-get update
apt-get install -y docker.io docker-compose-plugin git

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Clone and deploy
git clone https://github.com/your-org/breastguard-ai.git /opt/breastguard-ai
cd /opt/breastguard-ai
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Load Balancer Setup

**AWS Application Load Balancer:**

```bash
# Create target group
aws elbv2 create-target-group \
  --name breastguard-targets \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-12345678

# Create load balancer
aws elbv2 create-load-balancer \
  --name breastguard-alb \
  --subnets subnet-12345678 subnet-87654321 \
  --security-groups sg-12345678 \
  --type application \
  --scheme internet-facing

# Register targets
aws elbv2 register-targets \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --targets Id=i-1234567890abcdef0 Port=80
```

### 3. SSL/TLS Configuration

**Let's Encrypt (Recommended):**

```bash
# Install certbot
apt-get install -y certbot python3-certbot-nginx

# Generate certificates
certbot certonly --standalone -d breastguard.ai

# Configure automatic renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
```

**Traefik Automatic SSL:**

```yaml
# docker-compose.prod.yml
traefik:
  image: traefik:v3.0
  command:
    - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
    - "--certificatesresolvers.letsencrypt.acme.email=admin@breastguard.ai"
    - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
```

### 4. Monitoring Setup

**Prometheus Configuration:**

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'breastguard-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'breastguard-ml'
    static_configs:
      - targets: ['ml-service:8001']
    metrics_path: /metrics
    scrape_interval: 30s
```

**Grafana Dashboards:**

```bash
# Import pre-configured dashboards
curl -X POST \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana/dashboards/breastguard-overview.json \
  http://admin:password@localhost:3001/api/dashboards/db
```

## Scaling Guidelines

### Horizontal Scaling

**Backend API:**

```yaml
# docker-compose.prod.yml
backend:
  deploy:
    replicas: 3
    resources:
      limits:
        cpus: '1.0'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 1G
```

**ML Service:**

```yaml
ml-service:
  deploy:
    replicas: 2
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
        nvidia.com/gpu: 1
```

### Database Scaling

**PostgreSQL:**

```sql
-- Connection pooling
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';

-- Read replicas for scaling
CREATE USER replica_user WITH REPLICATION;
```

**Redis:**

```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## Security Hardening

### Network Security

```bash
# Firewall rules
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny 5432/tcp  # PostgreSQL (internal only)
ufw deny 6379/tcp  # Redis (internal only)
ufw deny 27017/tcp # MongoDB (internal only)
ufw enable
```

### Application Security

```bash
# Secure file permissions
chmod 600 .env
chmod 700 keys/
chmod 700 ssl/

# Remove sensitive files from image
echo "keys/" >> .dockerignore
echo "ssl/" >> .dockerignore
echo ".env" >> .dockerignore
```

## Backup and Recovery

### Database Backups

**PostgreSQL:**

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

docker-compose exec -T postgres pg_dump \
  -U breastguard_user \
  breastguard_ai | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"

# Retention: 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

**MongoDB:**

```bash
# MongoDB backup
#!/bin/bash
BACKUP_DIR="/backups/mongodb"
DATE=$(date +%Y%m%d_%H%M%S)

docker-compose exec -T mongo mongodump \
  --db breastguard_ai_docs \
  --gzip > "$BACKUP_DIR/mongodb_$DATE.gz"
```

### Application Backups

```bash
# Model and configuration backup
#!/bin/bash
BACKUP_DIR="/backups/application"
DATE=$(date +%Y%m%d_%H%M%S)

tar -czf "$BACKUP_DIR/application_$DATE.tar.gz" \
  models/ \
  keys/ \
  ssl/ \
  monitoring/
```

## Troubleshooting

### Common Issues

**1. Service Won't Start:**

```bash
# Check logs
docker-compose logs backend
docker-compose logs ml-service

# Check environment
docker-compose exec backend printenv | grep -E "(DATABASE|REDIS|JWT)"
```

**2. Database Connection Issues:**

```bash
# Test database connectivity
docker-compose exec backend python -c "
from backend.db import engine
try:
    engine.connect()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

**3. Memory Issues:**

```bash
# Monitor memory usage
docker stats --format "table {{.Container}}\t{{.MemUsage}}"

# Adjust limits
# Edit docker-compose.prod.yml resources section
```

**4. SSL Certificate Issues:**

```bash
# Verify certificates
openssl x509 -in ssl/cert.pem -text -noout
openssl rsa -in ssl/key.pem -check

# Test HTTPS
curl -v https://breastguard.ai/health
```

### Performance Optimization

**Database Optimization:**

```sql
-- PostgreSQL performance
CREATE INDEX CONCURRENTLY idx_analyses_user_created 
ON analyses(user_id, created_at);

ANALYZE analyses;
VACUUM ANALYZE analyses;
```

**Application Optimization:**

```yaml
# Connection pooling
backend:
  environment:
    - DB_POOL_SIZE=50
    - DB_MAX_OVERFLOW=100
    - CACHE_TTL_SECONDS=3600
```

## Maintenance

### Rolling Updates

```bash
# Zero-downtime deployment
#!/bin/bash

# Scale up new version
docker-compose -f docker-compose.v2.yml up -d --scale backend=3

# Wait for health checks
sleep 60

# Switch load balancer
# Update target group to point to new containers

# Scale down old version
docker-compose -f docker-compose.v1.yml down
```

### Health Monitoring

```bash
# Health check script
#!/bin/bash
SERVICES=("backend:8000/health" "ml-service:8001/health" "document-parser:8002/health")

for service in "${SERVICES[@]}"; do
    response=$(curl -s -o /dev/null -w "%{http_code}" http://$service)
    if [ $response != "200" ]; then
        echo "ALERT: $service is unhealthy"
        # Send notification
    fi
done
```

## Support

### Log Collection

```bash
# Centralized logging
docker-compose logs -f --tail=1000 > logs/breastguard-$(date +%Y%m%d).log &
```

### Monitoring Alerts

```yaml
# Prometheus alerting rules
groups:
  - name: breastguard-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
```

## Compliance

### HIPAA Requirements

- **Audit Logging**: All PHI access logged
- **Data Encryption**: Data encrypted at rest and in transit
- **Access Controls**: Role-based access control
- **Data Retention**: Configurable retention policies
- **Backup Procedures**: Regular automated backups

### GDPR Compliance

- **Data Minimization**: Only collect necessary data
- **Purpose Limitation**: Use data only for stated purposes
- **Storage Limitation**: Retain data only as long as necessary
- **Accuracy**: Maintain accurate and up-to-date data
- **Security**: Implement appropriate security measures

## Contact

For deployment support:
- **Documentation**: https://docs.breastguard.ai
- **Issues**: https://github.com/your-org/breastguard-ai/issues
- **Security**: security@breastguard.ai
- **Support**: support@breastguard.ai
