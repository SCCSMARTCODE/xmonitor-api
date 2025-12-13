# SafeX API - FastAPI Backend

**AI-Powered Safety Monitoring System Backend**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-via%20Supabase-336791.svg)](https://supabase.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL (via Supabase)
- Redis (for WebSocket pub/sub)
- Twilio Account (for SMS/calls)
- Cloudinary Account (for media storage)

### 1. Clone and Setup

```powershell
# Navigate to safex-api directory
cd C:\Users\PC\Desktop\safex-api

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```powershell
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
notepad .env
```

**Required Environment Variables:**
- `DATABASE_URL` - Supabase PostgreSQL connection (async)
- `SYNC_DATABASE_URL` - Supabase PostgreSQL connection (sync, for migrations)
- `SECRET_KEY` - JWT secret (min 32 characters)
- `REDIS_URL` - Redis connection string
- (Optional) `CLOUDINARY_*` - Cloudinary credentials
- (Optional) `TWILIO_*` - Twilio credentials

### 3. Initialize Database

```powershell
# Run Alembic migrations
alembic upgrade head
```

### 4. Run Server

```powershell
# Development mode (with auto-reload)
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**API will be available at:**
- Main API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📦 Project Structure

```
safex-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API route handlers
│   │       └── router.py        # Main API router
│   ├── core/
│   │   ├── config.py           # Configuration settings
│   │   ├── database.py         # Async database connection
│   │   ├── security.py         # JWT & password hashing
│   │   └── dependencies.py     # FastAPI dependencies
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── crud/                   # Database operations
│   ├── services/               # Business logic
│   └── utils/                  # Utility functions
├── alembic/                    # Database migrations
├── uploads/                    # Local media storage
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
└── .env                        # Environment variables
```

---

## 🔌 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `GET /api/v1/auth/me` - Get current user

### Camera Feeds
- `GET /api/v1/feeds` - List all feeds
- `POST /api/v1/feeds` - Create feed
- `PATCH /api/v1/feeds/{id}` - Update feed
- `DELETE /api/v1/feeds/{id}` - Delete feed
- `POST /api/v1/feeds/{id}/toggle` - Toggle feed status

### Alerts
- `GET /api/v1/alerts` - List alerts (with filters)
- `POST /api/v1/alerts` - Create alert (agent endpoint)
- `POST /api/v1/alerts/{id}/resolve` - Resolve alert

### Analytics
- `GET /api/v1/analytics/system-status` - System metrics
- `GET /api/v1/analytics/quick-stats` - Quick statistics
- `GET /api/v1/analytics/trends` - Detection trends

### WebSocket
- `/ws/monitoring` - Real-time updates

**[Full API Documentation →](http://localhost:8000/docs)**

---

## 🗄️ Database Migrations

### Create Migration

```powershell
alembic revision --autogenerate -m "description of changes"
```

### Apply Migrations

```powershell
# Upgrade to latest
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1
```

### View Migration History

```powershell
alembic history
alembic current
```

---

## 🔐 Security

- **JWT Authentication**: Access tokens (1 hour) + Refresh tokens (30 days)
- **Password Hashing**: Bcrypt with salt
- **CORS**: Configured for specific origins
- **SQL Injection**: Protected by SQLAlchemy ORM
- **Environment Variables**: Sensitive data never committed

---

## 🧪 Testing

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

---

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Generate strong `SECRET_KEY` (32+ characters)
- [ ] Configure production database (Supabase)
- [ ] Set up Redis instance
- [ ] Configure Cloudinary for media storage
- [ ] Set up Twilio for SMS/calls
- [ ] Update `ALLOWED_ORIGINS` with production URLs
- [ ] Run migrations: `alembic upgrade head`
- [ ] Use production ASGI server (Gunicorn + Uvicorn)

### Production Server

```bash
# Using Gunicorn with Uvicorn workers
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

---

## 📚 Documentation

- **Implementation Plan**: [implementation_plan.md](../../../.gemini/antigravity/brain/6b17de71-b89c-418d-b5ae-e16679a3f060/implementation_plan.md)
- **Task List**: [task.md](../../../.gemini/antigravity/brain/6b17de71-b89c-418d-b5ae-e16679a3f060/task.md)
- **API Spec**: [BACKEND_API_SPECIFICATION.md](../safex-ui/BACKEND_API_SPECIFICATION.md)

---

## 🤝 Integration

### SafeX Agent Integration

The Agent connects to the API to:
1. Create alerts when threats detected
2. Send real-time detection data
3. Log events
4. Update system metrics

**Agent Authentication**: JWT tokens (recommended) or API keys

### SafeX UI Integration

The UI fetches data from:
- System status and metrics
- Camera feed management
- Alerts with AI analysis
- Real-time updates via WebSocket

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🆘 Support

For issues or questions:
1. Check [implementation_plan.md](../../../.gemini/antigravity/brain/6b17de71-b89c-418d-b5ae-e16679a3f060/implementation_plan.md)
2. Review API documentation at `/docs`
3. Check database migrations: `alembic current`

---

**SafeX API v1.0.0** - Powering Intelligent Safety Monitoring 🛡️
