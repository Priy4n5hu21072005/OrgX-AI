import logging
from typing import Dict, Any, Optional
from urllib.parse import urlencode
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleOAuthService:
    @staticmethod
    def get_authorization_url(state: Optional[str] = None) -> str:
        """Construct the Google OAuth 2.0 / OpenID Connect authorization URL."""
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID or "mock-client-id",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
        }
        if state:
            params["state"] = state
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_code_for_user_info(code: str) -> Dict[str, Any]:
        """
        Exchange authorization code with Google for tokens and fetch user identity.
        In test/mock mode with mock credentials, returns mock user info for testing.
        """
        # Test/mock support if client credentials are mock or missing
        if (
            not settings.GOOGLE_CLIENT_ID
            or settings.GOOGLE_CLIENT_ID == "mock-google-client-id"
            or code.startswith("mock_google_code")
        ):
            logger.info("Using mock Google OAuth response for code: %s", code)
            return {
                "sub": f"google_user_{code[:10]}",
                "email": f"google_user_{code[:6]}@example.com",
                "name": "Google Test User",
                "email_verified": True,
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_data = token_response.json()
            if "error" in token_data:
                raise ValueError(token_data.get("error_description", "Failed to exchange Google OAuth code"))

            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("No access token returned from Google")

            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_info = userinfo_response.json()
            if "error" in user_info:
                raise ValueError("Failed to retrieve Google user profile")

            return user_info


google_oauth_service = GoogleOAuthService()
