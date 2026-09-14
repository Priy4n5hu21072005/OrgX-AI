from fastapi.testclient import TestClient
from app.services.redis_service import redis_service
from app.services.email_service import email_service


def test_register_user_success(client: TestClient):
    """Test standard user registration flow."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Priyanshu",
            "email": "user@gmail.com",
            "password": "StrongPassword123!",
        },
    )
    assert response.status_code == 201
    assert "User registered successfully" in response.json()["message"]

    # Verify OTP was saved in Redis
    otp = redis_service.get_email_otp("user@gmail.com")
    assert otp is not None
    assert len(otp) == 6

    # Verify email was dispatched/recorded
    assert len(email_service.sent_emails) == 1
    assert email_service.sent_emails[0]["to"] == "user@gmail.com"


def test_register_weak_password_validation(client: TestClient):
    """Test that weak passwords are rejected."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Priyanshu",
            "email": "weak@example.com",
            "password": "weak",
        },
    )
    assert response.status_code == 422


def test_register_duplicate_email(client: TestClient):
    """Test duplicate registration returns 409 Conflict."""
    payload = {
        "name": "Priyanshu",
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
    }
    res1 = client.post("/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["detail"] == "Email is already registered"


def test_verify_email_success_and_wrong_otp(client: TestClient):
    """Test email verification with wrong and correct OTPs."""
    client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "verify@example.com",
            "password": "StrongPassword123!",
        },
    )
    otp = redis_service.get_email_otp("verify@example.com")
    assert otp is not None

    # Try invalid OTP
    wrong_res = client.post(
        "/auth/verify-email",
        json={"email": "verify@example.com", "otp": "999999"},
    )
    assert wrong_res.status_code == 400
    assert wrong_res.json()["detail"] == "Invalid verification code"

    # Try valid OTP
    correct_res = client.post(
        "/auth/verify-email",
        json={"email": "verify@example.com", "otp": otp},
    )
    assert correct_res.status_code == 200
    assert "Email verified successfully" in correct_res.json()["message"]

    # Verify OTP was deleted from Redis
    assert redis_service.get_email_otp("verify@example.com") is None


def test_login_flow(client: TestClient):
    """Test login before verification, after verification, and with wrong credentials."""
    email = "login_test@example.com"
    password = "StrongPassword123!"

    client.post(
        "/auth/register",
        json={"name": "Login User", "email": email, "password": password},
    )

    # 1. Login before email verification -> should return 403 Forbidden
    unverified_login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert unverified_login.status_code == 403
    assert "Email is not verified" in unverified_login.json()["detail"]

    # 2. Verify email
    otp = redis_service.get_email_otp(email)
    client.post("/auth/verify-email", json={"email": email, "otp": otp})

    # 3. Wrong password -> 401
    bad_pw_res = client.post(
        "/auth/login",
        json={"email": email, "password": "WrongPassword123!"},
    )
    assert bad_pw_res.status_code == 401

    # 4. Correct login -> 200 + token
    success_login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert success_login.status_code == 200
    data = success_login.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email


def test_forgot_and_reset_password_flow(client: TestClient):
    """Test forgot password, token single use, and password reset."""
    email = "forgot_test@example.com"
    old_pw = "OldPassword123!"
    new_pw = "NewStrongPassword123!"

    # Register & verify user
    client.post(
        "/auth/register",
        json={"name": "Forgot User", "email": email, "password": old_pw},
    )
    otp = redis_service.get_email_otp(email)
    client.post("/auth/verify-email", json={"email": email, "otp": otp})

    # Request password reset
    forgot_res = client.post(
        "/auth/forgot-password",
        json={"email": email},
    )
    assert forgot_res.status_code == 200
    assert "password reset link has been sent" in forgot_res.json()["message"]

    # Find reset token from sent email
    reset_emails = [e for e in email_service.sent_emails if "Reset your OrgX-AI password" in e["subject"]]
    assert len(reset_emails) == 1
    # Extract token from url query string
    body = reset_emails[0]["body"]
    token_str = body.split("token=")[1].split("\n")[0].strip()

    # Reset password with valid token
    reset_res = client.post(
        "/auth/reset-password",
        json={"token": token_str, "new_password": new_pw},
    )
    assert reset_res.status_code == 200

    # Ensure single use: second reset attempt with same token fails
    reused_res = client.post(
        "/auth/reset-password",
        json={"token": token_str, "new_password": new_pw},
    )
    assert reused_res.status_code == 400

    # Test login with old password fails
    old_login = client.post("/auth/login", json={"email": email, "password": old_pw})
    assert old_login.status_code == 401

    # Test login with new password succeeds
    new_login = client.post("/auth/login", json={"email": email, "password": new_pw})
    assert new_login.status_code == 200


def test_google_oauth_endpoints(client: TestClient):
    """Test Google OAuth login URL generator and callback handler."""
    # 1. Google login URL endpoint
    login_url_res = client.get("/auth/google/login")
    assert login_url_res.status_code == 200
    assert "accounts.google.com" in login_url_res.json()["authorization_url"]

    # 2. Google callback endpoint
    callback_res = client.get("/auth/google/callback?code=mock_google_code_12345")
    assert callback_res.status_code == 200
    data = callback_res.json()
    assert "access_token" in data
    assert data["user"]["auth_provider"] == "google"
    assert data["user"]["is_email_verified"] is True


def test_resend_verification_otp(client: TestClient):
    """Test resending verification OTP for unverified and verified accounts."""
    email = "resend_test@example.com"
    client.post(
        "/auth/register",
        json={"name": "Resend User", "email": email, "password": "StrongPassword123!"},
    )

    first_otp = redis_service.get_email_otp(email)
    assert first_otp is not None

    # Resend OTP
    resend_res = client.post("/auth/resend-verification", json={"email": email})
    assert resend_res.status_code == 200
    assert "verification code has been sent" in resend_res.json()["message"]

    second_otp = redis_service.get_email_otp(email)
    assert second_otp is not None

    # Verify email
    client.post("/auth/verify-email", json={"email": email, "otp": second_otp})

    # Resending for already verified email returns 400
    verified_resend = client.post("/auth/resend-verification", json={"email": email})
    assert verified_resend.status_code == 400
    assert "already verified" in verified_resend.json()["detail"]


def test_root_and_health_endpoints(client: TestClient):
    """Test public health check and landing endpoints."""
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"

    root_res = client.get("/")
    assert root_res.status_code == 200
    assert "docs" in root_res.json()
