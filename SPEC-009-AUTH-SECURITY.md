# SPEC-009: Authentication & Security

## Context
Currently, `frontend/src/lib/http.ts` looks for a token in `localStorage`, but the backend validates nothing.

## Requirements
- **Standard:** OAuth2 with Password Flow (Simple, local).
- **Secret:** Generated on startup, printed to console (like Jupyter).

## Implementation Guide

### 1. Backend Deps
`pip install python-jose passlib[bcrypt]`

### 2. `backend/app/services/auth_service.py`
```python
from jose import jwt
from datetime import datetime, timedelta
from app.config import get_settings

SECRET_KEY = get_settings().auth_secret
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30) # Long expiry for local tool
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    # ... Standard JWT decode logic ...
```

### 3. Secure the Routes
Update backend/app/main.py to add a global dependency or per-router dependency on verify_token.