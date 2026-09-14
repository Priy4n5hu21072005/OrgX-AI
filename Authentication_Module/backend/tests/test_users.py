from fastapi.testclient import TestClient
from app.services.redis_service import redis_service


def test_get_current_user_profile_and_logout(client: TestClient):
    """Test protected /users/me endpoint and token revocation on logout."""
    email = "profile_test@example.com"
    password = "StrongPassword123!"

    # Register, verify, and log in
    client.post(
        "/auth/register",
        json={"name": "Profile User", "email": email, "password": password},
    )
    otp = redis_service.get_email_otp(email)
    client.post("/auth/verify-email", json={"email": email, "otp": otp})

    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["access_token"]

    # 1. Unauthenticated request to /users/me -> 401
    unauth_res = client.get("/users/me")
    assert unauth_res.status_code == 401

    # 2. Authenticated request with Bearer token -> 200
    headers = {"Authorization": f"Bearer {token}"}
    auth_res = client.get("/users/me", headers=headers)
    assert auth_res.status_code == 200
    assert auth_res.json()["email"] == email
    assert auth_res.json()["name"] == "Profile User"

    # 3. Logout
    logout_res = client.post("/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Successfully logged out."

    # 4. Accessing /users/me after logout -> 401 Revoked
    revoked_res = client.get("/users/me", headers=headers)
    assert revoked_res.status_code == 401
    assert "revoked" in revoked_res.json()["detail"].lower()
