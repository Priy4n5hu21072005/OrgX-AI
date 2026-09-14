# OrgX-AI Authentication Module API

Production-grade, API-only authentication backend for **OrgX-AI**, built strictly according to the architecture in [`Authentication_Module/OrgX-AI_Authentication_Module.md`](../Authentication_Module/OrgX-AI_Authentication_Module.md).

## 🚀 Features

- **Email + Password Registration**: Argon2id password hashing, strong password validation.
- **Email Verification**: 6-digit numeric OTP stored in Redis with automatic 15-minute TTL.
- **Authentication & JWT**: Secure session handling using JWT bearer tokens.
- **Forgot Password**: Enumeration-safe reset request, cryptographically secure single-use token sent via SMTP/Gmail with 15-minute TTL in Redis.
- **Password Reset**: Secure reset endpoint validating and consuming single-use tokens from Redis.
- **Google OAuth 2.0 / OpenID Connect**: Social login for seamless account creation and linking.
- **Token Invalidation / Logout**: Redis-based token blacklist preventing reused revoked JWTs.
- **Protected Endpoints**: FastAPI `get_current_user` dependency for route authorization (`/users/me`).
- **Resilient Fallback**: Automatic in-memory cache fallback for Redis and SQLite support for zero-config offline development.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Framework | **FastAPI** |
| Server | **Uvicorn** |
| ORM | **SQLAlchemy 2.0** |
| Migrations | **Alembic** |
| Database | **PostgreSQL** (with SQLite dev fallback) |
| Password Hashing | **Argon2id** (`argon2-cffi`) |
| Auth Tokens | **PyJWT** |
| Temporary Cache | **Redis** (with in-memory fallback) |
| Social Login | **Google OAuth 2.0 / OpenID Connect** |
| Validation | **Pydantic v2** (`pydantic-settings`, `email-validator`) |
| Testing | **Pytest** + **HTTPX** |

---

## 📁 Project Structure

```text
backend/
├── app/
│   ├── main.py                  # FastAPI application entrypoint & middleware
│   ├── core/
│   │   ├── config.py            # Environment configuration
│   │   ├── database.py          # SQLAlchemy engine & session management
│   │   └── security.py          # Argon2id hashing & JWT token management
│   ├── models/
│   │   └── user.py              # User database model
│   ├── schemas/
│   │   ├── auth.py              # Auth request & response schemas
│   │   └── user.py              # User representation schemas
│   ├── routers/
│   │   ├── auth.py              # Authentication endpoints
│   │   └── users.py             # User profile endpoints
│   ├── services/
│   │   ├── auth_service.py      # Core authentication workflows
│   │   ├── email_service.py     # SMTP / Gmail email dispatch
│   │   ├── google_service.py    # Google OAuth 2.0 / OpenID Connect service
│   │   └── redis_service.py     # OTP, reset token, & token blacklist store
│   ├── dependencies/
│   │   └── auth.py              # get_current_user security dependency
│   └── utils/
│       └── tokens.py            # OTP and reset token generators
├── alembic/                     # Database migrations
├── tests/                       # Complete pytest test suite
├── .env.example                 # Environment configuration template
├── requirements.txt             # Python dependencies
└── README.md
```

---

## ⚡ Quick Start

### 1. Installation

Install dependencies:
```bash
py -m pip install -r requirements.txt
```

### 2. Configure Environment

Copy the `.env.example` file:
```bash
cp .env.example .env
```

Default settings in `.env` are configured for instant local development. For production:
- Set `DATABASE_URL` to your PostgreSQL instance: `postgresql://user:password@localhost:5432/orgx_auth`
- Set `REDIS_URL` to your Redis instance: `redis://localhost:6379/0`
- Set `SMTP_USERNAME` and `SMTP_PASSWORD` for live Gmail/SMTP dispatch.
- Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` for Google OAuth.

### 3. Run Migrations

```bash
py -m alembic upgrade head
```

### 4. Start Development Server

```bash
py -m uvicorn app.main:app --reload --port 8000
```

Interactive Swagger API docs will be available at:
👉 **`http://127.0.0.1:8000/docs`**

Alternative ReDoc at:
👉 **`http://127.0.0.1:8000/redoc`**

---

## 🧪 Running Tests

Run the full automated test suite:
```bash
py -m pytest tests -v
```

---

## 📡 API Endpoints Catalog

### 1. Registration & Verification

#### `POST /auth/register`
Creates a new unverified user and sends a 6-digit OTP to the provided email.
```json
// Request
{
  "name": "Priyanshu",
  "email": "user@example.com",
  "password": "StrongPassword123!"
}
// Response (201 Created)
{
  "message": "User registered successfully. Please check your email for the verification code.",
  "detail": null
}
```

#### `POST /auth/verify-email`
Verifies account with the 6-digit OTP stored in Redis.
```json
// Request
{
  "email": "user@example.com",
  "otp": "123456"
}
// Response (200 OK)
{
  "message": "Email verified successfully. You can now log in.",
  "detail": null
}
```

#### `POST /auth/resend-verification`
Generates and emails a fresh OTP.
```json
// Request
{
  "email": "user@example.com"
}
```

---

### 2. Login & Profile

#### `POST /auth/login`
Authenticates against Argon2id hash and returns Bearer JWT.
```json
// Request
{
  "email": "user@example.com",
  "password": "StrongPassword123!"
}
// Response (200 OK)
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "name": "Priyanshu",
    "email": "user@example.com",
    "auth_provider": "local",
    "google_id": null,
    "is_email_verified": true,
    "is_active": true,
    "created_at": "2026-09-14T11:50:00Z",
    "updated_at": "2026-09-14T11:50:00Z"
  }
}
```

#### `GET /users/me`
Requires `Authorization: Bearer <JWT>`. Returns authenticated user profile.

#### `POST /auth/logout`
Requires `Authorization: Bearer <JWT>`. Revokes token via Redis blacklist.

---

### 3. Forgot & Reset Password

#### `POST /auth/forgot-password`
Enumeration-safe password reset trigger.
```json
// Request
{
  "email": "user@example.com"
}
// Response (200 OK)
{
  "message": "If an account exists for this email, a password reset link has been sent.",
  "detail": null
}
```

#### `POST /auth/reset-password`
Consumes single-use token from Redis and updates Argon2id password hash.
```json
// Request
{
  "token": "4fA9z...",
  "new_password": "NewStrongPassword123!"
}
// Response (200 OK)
{
  "message": "Password has been reset successfully. You can now log in with your new password.",
  "detail": null
}
```

---

### 4. Google OAuth 2.0 / OpenID Connect

#### `GET /auth/google/login`
Returns Google OAuth 2.0 authorization URL. Pass `?redirect=true` to redirect immediately.

#### `GET /auth/google/callback?code=<CODE>&state=<STATE>`
Exchanges authorization code for Google user profile, links or provisions user, and issues a JWT.
