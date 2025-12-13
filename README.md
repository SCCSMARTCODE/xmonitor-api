# FastAPI Application
MIT License

## License

- Review CORS settings for production
- Consider using HTTPS in production
- Use strong passwords
- Change `SECRET_KEY` in `.env` before deploying to production

## Security Notes

4. Import model in `app/models/__init__.py`
3. Create CRUD operations in `app/crud/`
2. Create corresponding schemas in `app/schemas/`
1. Create model in `app/models/`

### Adding new models

3. Include the router in `app/api/v1/router.py`
2. Define your routes in the new file
1. Create a new endpoint file in `app/api/v1/endpoints/`

### Adding new endpoints

## Development

- **users** - User accounts with authentication

### Tables

The application uses SQLite database (`app.db`) which will be automatically created on first run.

## Database

```
curl -X GET "http://localhost:8000/api/v1/users"
```bash

### Get users list

```
  }'
    "password": "secure_password"
    "username": "johndoe",
  -d '{
  -H "Content-Type: application/json" \
curl -X POST "http://localhost:8000/api/v1/users/login" \
```bash

### Login

```
  }'
    "full_name": "John Doe"
    "password": "secure_password",
    "username": "johndoe",
    "email": "user@example.com",
  -d '{
  -H "Content-Type: application/json" \
curl -X POST "http://localhost:8000/api/v1/users/register" \
```bash

### Register a new user

## Usage Examples

- `GET /api/v1/users` - Get list of users
- `POST /api/v1/users/login` - Login and get access token
- `POST /api/v1/users/register` - Register a new user
### User Management

- `GET /health` - Health check
- `GET /` - Root endpoint
### Health Check

## API Endpoints

- ReDoc: http://localhost:8000/redoc
- Swagger UI: http://localhost:8000/docs
- Main API: http://localhost:8000
The API will be available at:

```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Or use uvicorn directly

python main.py
# Development mode with auto-reload
```bash

### 4. Run the application

- Modify other settings as required
- Adjust CORS origins
- Update `SECRET_KEY` for production
Copy `.env` and update settings as needed:

### 3. Configure environment

```
pip install -r requirements.txt
```bash

### 2. Install dependencies

```
source .venv/bin/activate
# Activate (Linux/Mac)

.venv\Scripts\activate.bat
# Activate (Windows CMD)

.\.venv\Scripts\Activate.ps1
# Activate (Windows PowerShell)

python -m venv .venv
# Create virtual environment
```bash

### 1. Create and activate virtual environment

## Installation

```
└── README.md              # This file
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
├── main.py                 # Application entry point
│       └── user.py         # Pydantic schemas
│       ├── __init__.py
│   └── schemas/
│   │   └── user.py         # SQLAlchemy models
│   │   ├── __init__.py
│   ├── models/
│   │   └── user.py         # CRUD operations for users
│   │   ├── __init__.py
│   ├── crud/
│   │   └── security.py     # JWT & password hashing
│   │   ├── database.py     # Database connection & session
│   │   ├── config.py       # Configuration settings
│   │   ├── __init__.py
│   ├── core/
│   │           └── users.py
│   │           ├── __init__.py
│   │       └── endpoints/
│   │       ├── router.py
│   │       ├── __init__.py
│   │   └── v1/
│   │   ├── __init__.py
│   ├── api/
│   ├── __init__.py
├── app/
safex-api/
```

## Project Structure

- ✅ Auto-generated API documentation (Swagger UI & ReDoc)
- ✅ CORS middleware
- ✅ CRUD operations
- ✅ Pydantic schemas for validation
- ✅ User registration and login endpoints
- ✅ Password hashing with bcrypt
- ✅ JWT authentication
- ✅ SQLite database with SQLAlchemy ORM
- ✅ FastAPI framework

## Features

A production-ready FastAPI application with SQLite database, SQLAlchemy ORM, JWT authentication, and user management.


