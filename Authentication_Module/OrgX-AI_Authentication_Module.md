# OrgX-AI Authentication Module

## 1. Objective

OrgX-AI ke liye ek complete, production-style authentication system build karna hai jisme:

- Email + Password Registration
- Email Verification
- Login
- JWT based authentication
- Forgot Password
- Gmail par Password Reset Link
- Reset Password Web Page
- Google OAuth 2.0 / OpenID Connect Login
- Secure Password Hashing using Argon2id
- Redis for OTP / temporary reset-token storage
- PostgreSQL for permanent user data
- Protected API routes
- Frontend route protection
- Logout / token handling
- Proper validation and error handling

---

# 2. Overall Architecture

```text
                         ORGX-AI
                            |
                 +----------+----------+
                 |                     |
             FRONTEND                BACKEND
              React                  FastAPI
                 |                     |
                 |             +-------+-------+
                 |             |       |       |
                 |         PostgreSQL Redis  Google OAuth
                 |             |       |
                 +-------------+-------+
                       API / JWT
```

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Backend | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migration | Alembic |
| Password Hashing | Argon2id |
| Authentication | JWT |
| Temporary Data | Redis |
| Email | SMTP / Gmail |
| Social Login | Google OAuth 2.0 / OpenID Connect |
| Validation | Pydantic v2 |

---

# 3. Authentication Flows

The system will have four major authentication flows:

1. Registration
2. Login
3. Forgot Password / Reset Password
4. Continue with Google

---

# 4. Registration Flow

## Frontend

Registration page:

```text
+--------------------------------+
|          Create Account        |
|                                |
| Name                           |
| [________________________]     |
|                                |
| Email                          |
| [________________________]     |
|                                |
| Password                       |
| [________________________]     |
|                                |
| Confirm Password               |
| [________________________]     |
|                                |
|       [ Create Account ]       |
|                                |
|      Continue with Google      |
|                                |
| Already have an account? Login |
+--------------------------------+
```

Frontend responsibilities:

- Input fields
- Client-side validation
- Password confirmation
- Loading state
- API request
- Display backend errors
- Redirect after successful registration

Example request:

```http
POST /auth/register
```

```json
{
  "name": "Priyanshu",
  "email": "user@gmail.com",
  "password": "StrongPassword123!"
}
```

## Backend

FastAPI receives the request.

Steps:

```text
Receive request
      ↓
Validate input
      ↓
Check if email already exists
      ↓
Hash password using Argon2id
      ↓
Create verification OTP/token
      ↓
Store temporary OTP in Redis
      ↓
Send verification email
      ↓
Return success response
```

Important:

**Plain-text password kabhi PostgreSQL mein store nahi hoga.**

Only Argon2id hash will be stored.

---

# 5. Email Verification

Registration ke baad user ko verification email milega.

Example:

```text
Subject: Verify your OrgX-AI account

Welcome to OrgX-AI!

Please verify your email to activate your account.

Your verification code:
123456
```

Frontend:

```text
Verify Email

Enter OTP:
[ _ _ _ _ _ _ ]

[ Verify Email ]

Resend OTP
```

Backend endpoint:

```http
POST /auth/verify-email
```

Request:

```json
{
  "email": "user@gmail.com",
  "otp": "123456"
}
```

Backend:

```text
Get OTP from Redis
      ↓
Compare OTP
      ↓
Check expiry
      ↓
Mark email as verified
      ↓
Delete OTP from Redis
      ↓
Success
```

---

# 6. Login Flow

Frontend login page:

```text
+--------------------------------+
|             Login              |
|                                |
| Email                          |
| [________________________]     |
|                                |
| Password                       |
| [________________________]     |
|                                |
|          Forgot Password?      |
|                                |
|          [ Login ]             |
|                                |
|      Continue with Google      |
|                                |
| Don't have an account? Sign Up |
+--------------------------------+
```

Request:

```http
POST /auth/login
```

```json
{
  "email": "user@gmail.com",
  "password": "StrongPassword123!"
}
```

Backend:

```text
Receive credentials
      ↓
Find user in PostgreSQL
      ↓
Verify password with Argon2id
      ↓
Check email verification
      ↓
Generate JWT
      ↓
Return authentication response
```

Example response:

```json
{
  "access_token": "JWT_TOKEN",
  "token_type": "bearer"
}
```

---

# 7. JWT Authentication

JWT will be used for authenticated API requests.

Flow:

```text
Login
  ↓
FastAPI creates JWT
  ↓
Frontend receives token
  ↓
Frontend stores authentication state
  ↓
Frontend sends token with protected requests
```

Protected request:

```http
Authorization: Bearer <JWT>
```

Example:

```http
GET /users/me
Authorization: Bearer eyJ...
```

Backend:

```text
Extract JWT
    ↓
Verify signature
    ↓
Check expiry
    ↓
Extract user ID
    ↓
Load user
    ↓
Allow request
```

JWT payload should contain only necessary information, for example:

```json
{
  "sub": "user_id",
  "exp": "expiration_time"
}
```

Do not put passwords or sensitive information inside JWT.

---

# 8. Forgot Password Flow

This is an important part of the module.

Frontend:

```text
Forgot Password?

Email
[________________________]

[ Send Reset Link ]
```

Request:

```http
POST /auth/forgot-password
```

```json
{
  "email": "user@gmail.com"
}
```

Backend:

```text
Receive email
      ↓
Find user
      ↓
Generate secure random reset token
      ↓
Store token in Redis with expiry
      ↓
Create reset URL
      ↓
Send reset link through Gmail
```

Example email:

```text
Subject: Reset your OrgX-AI password

We received a request to reset your password.

Click the link below:

https://orgx-ai.com/reset-password?token=RANDOM_TOKEN

This link expires in 15 minutes.

If you did not request this, ignore this email.
```

---

# 9. Reset Password Frontend

When user clicks the Gmail link:

```text
https://orgx-ai.com/reset-password?token=RANDOM_TOKEN
```

React opens:

```text
/reset-password
```

The frontend reads the token from the URL.

Page:

```text
+--------------------------------+
|        Reset Password          |
|                                |
| New Password                   |
| [________________________]     |
|                                |
| Confirm Password               |
| [________________________]     |
|                                |
|       [ Reset Password ]       |
+--------------------------------+
```

Frontend responsibilities:

1. Read token from URL
2. Validate password
3. Check confirm password
4. Show loading state
5. Send token + new password to backend
6. Show success/error
7. Redirect user to login

Request:

```http
POST /auth/reset-password
```

```json
{
  "token": "RANDOM_TOKEN",
  "new_password": "NewStrongPassword123!"
}
```

Backend:

```text
Receive token
      ↓
Find token in Redis
      ↓
Check token validity
      ↓
Check expiration
      ↓
Find associated user
      ↓
Hash new password using Argon2id
      ↓
Update PostgreSQL
      ↓
Delete reset token from Redis
      ↓
Return success
```

The reset token must be **one-time use**.

---

# 10. Google OAuth

Google OAuth is different from Google Authenticator.

For OrgX-AI we need:

**Google OAuth 2.0 / OpenID Connect**

Not Google Authenticator.

Login page:

```text
[ Continue with Google ]
```

Flow:

```text
User clicks Continue with Google
          ↓
Frontend redirects to Google
          ↓
Google authentication
          ↓
Google gives authorization result
          ↓
Backend verifies Google identity
          ↓
Find/create user
          ↓
Generate OrgX-AI JWT
          ↓
User logged in
```

Important:

Google OAuth should be an additional login method.

The normal Email + Password authentication will still exist.

---

# 11. User Database Schema

Recommended `users` table:

```text
users
--------------------------------
id
name
email
password_hash
auth_provider
google_id
is_email_verified
is_active
created_at
updated_at
```

Suggested meaning:

| Field | Purpose |
|---|---|
| id | Unique user ID |
| name | User's name |
| email | Unique email |
| password_hash | Argon2id password hash |
| auth_provider | local / google |
| google_id | Google account identifier |
| is_email_verified | Verification status |
| is_active | Account status |
| created_at | Creation timestamp |
| updated_at | Last update |

For Google-only users, `password_hash` can be nullable because their authentication is handled by Google.

---

# 12. Redis Data

Redis should handle short-lived authentication data.

Examples:

```text
email_verification:<email>
forgot_password:<token>
```

Example:

```text
forgot_password:abc123xyz
        ↓
user_id
        ↓
TTL = 15 minutes
```

Redis is useful because OTPs and reset tokens are temporary and need automatic expiry.

---

# 13. FastAPI Backend Structure

Recommended structure:

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   │
│   ├── models/
│   │   └── user.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   └── user.py
│   │
│   ├── routers/
│   │   ├── auth.py
│   │   └── users.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── email_service.py
│   │   ├── google_service.py
│   │   └── redis_service.py
│   │
│   ├── dependencies/
│   │   └── auth.py
│   │
│   └── utils/
│       └── tokens.py
│
├── alembic/
├── tests/
├── .env
├── requirements.txt
└── README.md
```

---

# 14. Important Backend Endpoints

## Registration

```http
POST /auth/register
```

## Verify Email

```http
POST /auth/verify-email
```

## Resend Verification

```http
POST /auth/resend-verification
```

## Login

```http
POST /auth/login
```

## Google OAuth

```http
GET /auth/google/login
GET /auth/google/callback
```

## Forgot Password

```http
POST /auth/forgot-password
```

## Reset Password

```http
POST /auth/reset-password
```

## Current User

```http
GET /users/me
```

## Logout

```http
POST /auth/logout
```

---

# 15. Frontend Structure

Recommended:

```text
frontend/
│
├── src/
│   ├── components/
│   │   ├── Navbar.jsx
│   │   ├── ProtectedRoute.jsx
│   │   ├── AuthInput.jsx
│   │   └── Loading.jsx
│   │
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── VerifyEmail.jsx
│   │   ├── ForgotPassword.jsx
│   │   ├── ResetPassword.jsx
│   │   └── Dashboard.jsx
│   │
│   ├── services/
│   │   └── authApi.js
│   │
│   ├── context/
│   │   └── AuthContext.jsx
│   │
│   ├── hooks/
│   │   └── useAuth.js
│   │
│   ├── routes/
│   │   └── AppRoutes.jsx
│   │
│   ├── App.jsx
│   └── main.jsx
│
└── package.json
```

---

# 16. Frontend Routes

Public routes:

```text
/login
/register
/forgot-password
/verify-email
/reset-password
```

Protected routes:

```text
/dashboard
/profile
/settings
```

Google callback route can be handled according to the selected OAuth architecture.

---

# 17. ProtectedRoute

Frontend should prevent unauthenticated users from accessing protected pages.

Example logic:

```text
User opens /dashboard
        ↓
Is user authenticated?
        ↓
   YES       NO
    ↓         ↓
Dashboard   /login
```

Backend protection is still mandatory.

Frontend route protection is only for user experience; it is **not a security boundary**.

---

# 18. Authentication State

React should maintain authentication state using an `AuthContext` or equivalent state-management approach.

Example:

```text
AuthContext
    |
    +-- user
    +-- isAuthenticated
    +-- loading
    +-- login()
    +-- logout()
```

On application startup:

```text
App starts
   ↓
Check authentication state
   ↓
Fetch current user if authenticated
   ↓
Set user
   ↓
Render application
```

---

# 19. Frontend API Service

Keep API calls separate from UI components.

Example:

```text
services/authApi.js

register()
login()
verifyEmail()
resendVerification()
forgotPassword()
resetPassword()
getCurrentUser()
logout()
```

This keeps components clean and makes the code easier to maintain.

---

# 20. Validation

Frontend validation:

- Required fields
- Valid email
- Minimum password length
- Password confirmation
- Basic password strength
- Prevent empty submissions

Backend validation:

- Pydantic schemas
- Email validation
- Password validation
- Database checks
- Token validation
- Authorization

Backend validation must always exist even if frontend validation exists.

---

# 21. Error Handling

Backend should return meaningful HTTP responses.

Examples:

```text
400 → Invalid request
401 → Invalid credentials
403 → Not authorized
404 → Resource not found
409 → Email already registered
422 → Validation error
500 → Internal server error
```

Frontend should display user-friendly messages.

Example:

```text
Invalid email or password.

Email is already registered.

Reset link has expired.

Password reset successful.
```

Avoid exposing unnecessary internal errors.

---

# 22. Security Requirements

## Password

Never store:

```text
password = "mypassword123"
```

Store:

```text
password_hash = "$argon2id$..."
```

## Reset Token

Reset tokens must be:

- Cryptographically random
- Short-lived
- One-time use
- Stored securely
- Invalidated after successful reset

## JWT

JWT should:

- Have an expiration time
- Be cryptographically signed
- Contain minimal claims
- Never contain passwords/secrets

## Email Enumeration

Forgot-password responses should ideally not reveal whether an email exists.

For example:

```text
"If an account exists for this email,
a password reset link has been sent."
```

This prevents attackers from discovering registered emails.

---

# 23. Environment Variables

Secrets must not be hardcoded.

Example `.env`:

```text
DATABASE_URL=...

REDIS_URL=...

JWT_SECRET_KEY=...

GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=...

SMTP_HOST=...
SMTP_PORT=...
SMTP_USERNAME=...
SMTP_PASSWORD=...

FRONTEND_URL=...
```

`.env` must be added to `.gitignore`.

Never push secrets to GitHub.

---

# 24. Email Service

Create a separate email service.

Responsibilities:

```text
EmailService
    |
    +-- send_verification_email()
    |
    +-- send_password_reset_email()
    |
    +-- send_welcome_email()
```

This will make the authentication module easier to extend later.

---

# 25. Recommended Development Order

Team ko parallel kaam karne ke liye module ko phases mein divide karna best rahega.

## Phase 1 — Backend Foundation

- FastAPI setup
- PostgreSQL setup
- SQLAlchemy setup
- Alembic
- User model
- Pydantic schemas
- Environment configuration

## Phase 2 — Registration

- Register endpoint
- Argon2id
- Email verification
- Redis OTP
- SMTP email

## Phase 3 — Login

- Login endpoint
- Password verification
- JWT generation
- Authentication dependency
- `/users/me`

## Phase 4 — Forgot Password

- Forgot password endpoint
- Secure reset token
- Redis TTL
- Gmail reset email
- Reset password endpoint

## Phase 5 — Google OAuth

- Google Cloud project
- OAuth credentials
- Authorization URL
- Callback
- Google identity verification
- User creation/login
- JWT generation

## Phase 6 — Frontend

- Login
- Register
- Verify Email
- Forgot Password
- Reset Password
- Google Login
- Protected Routes
- Auth Context
- API service
- Error/loading states

## Phase 7 — Testing

Test:

- Register
- Duplicate email
- Wrong OTP
- Expired OTP
- Login
- Wrong password
- Unverified account
- Forgot password
- Expired reset link
- Used reset link
- Password reset
- Google login
- Protected APIs
- Logout

---

# 26. Team Work Division

Suggested division:

### Backend Developer

Responsible for:

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Redis
- JWT
- Argon2id
- Auth endpoints
- Google OAuth backend
- Email service

### Frontend Developer

Responsible for:

- Login UI
- Registration UI
- Verify Email UI
- Forgot Password UI
- Reset Password UI
- Google Login button
- Protected routes
- Auth state
- API integration
- Loading/error states

### Integration / Testing

Responsible for:

- API testing
- Frontend-backend integration
- Authentication edge cases
- Security testing
- Deployment environment variables
- Documentation

---

# 27. Complete User Journey

## New User

```text
Register
   ↓
Verification Email
   ↓
Verify Email
   ↓
Login
   ↓
JWT
   ↓
Dashboard
```

## Existing User

```text
Login
   ↓
JWT
   ↓
Dashboard
```

## Forgot Password

```text
Login
  ↓
Forgot Password
  ↓
Enter Email
  ↓
Gmail Reset Link
  ↓
Click Link
  ↓
Reset Password Page
  ↓
New Password
  ↓
Password Updated
  ↓
Login
```

## Google User

```text
Login
  ↓
Continue with Google
  ↓
Google Authentication
  ↓
Backend Verification
  ↓
JWT
  ↓
Dashboard
```

---

# 28. Final Architecture

```text
                         React Frontend
                              |
        +---------------------+---------------------+
        |                     |                     |
      Login                Register            Google Login
        |                     |                     |
        +---------------------+---------------------+
                              |
                           FastAPI
                              |
        +----------+----------+----------+----------+
        |          |                     |          |
     JWT Auth   User Service        Email Service  OAuth
        |          |                     |          |
        |          ↓                     ↓          ↓
        |      PostgreSQL              Gmail      Google
        |
      Redis
        |
   OTP / Reset Token
```

---

# 29. Definition of Done

Authentication module tab complete maana jayega jab:

- [ ] User registration works
- [ ] Password is stored using Argon2id
- [ ] Email verification works
- [ ] Login works
- [ ] JWT authentication works
- [ ] Protected APIs work
- [ ] Forgot password works
- [ ] Gmail reset link works
- [ ] Reset Password page works
- [ ] Expired reset token is rejected
- [ ] Reset token is one-time use
- [ ] Google OAuth works
- [ ] Logout works
- [ ] Frontend protected routes work
- [ ] Backend authorization works
- [ ] Validation and error handling work
- [ ] Secrets are stored in environment variables
- [ ] Authentication flows are tested
- [ ] README/API documentation is updated

---

# 30. Important Note

Google OAuth and Google Authenticator are not the same.

For this project:

```text
Google OAuth
    ↓
"Continue with Google"
    ↓
Social Login
```

Google Authenticator would only be needed if OrgX-AI later adds:

```text
Two-Factor Authentication (2FA/MFA)
```

That can be added as a future security feature.
