from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import security_scheme, get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    MessageResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import auth_service
from app.services.google_service import google_oauth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user with Argon2id password hashing and sends an email verification OTP.",
)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    auth_service.register_user(db, request)
    return MessageResponse(
        message="User registered successfully. Please check your email for the verification code."
    )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify email with OTP",
    description="Validates the 6-digit OTP stored in Redis and activates the account.",
)
def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    auth_service.verify_email(db, request.email, request.otp)
    return MessageResponse(
        message="Email verified successfully. You can now log in."
    )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend verification OTP",
    description="Resends a new 6-digit verification OTP to the user's email if not already verified.",
)
def resend_verification(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    auth_service.resend_verification_otp(db, request.email)
    return MessageResponse(
        message="A new verification code has been sent to your email."
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticates credentials with Argon2id, verifies email activation status, and issues a JWT.",
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user, token = auth_service.login_user(db, request)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/google/login",
    summary="Initiate Google OAuth 2.0 Login",
    description="Generates the Google OAuth 2.0 / OpenID Connect authorization URL. Set ?redirect=true to perform 307 redirect.",
)
def google_login(
    state: Optional[str] = None,
    redirect: bool = Query(False, description="If true, redirects directly to Google auth page"),
):
    auth_url = google_oauth_service.get_authorization_url(state=state)
    if redirect:
        return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    return {"authorization_url": auth_url}


@router.get(
    "/google/callback",
    response_model=TokenResponse,
    summary="Google OAuth 2.0 Callback",
    description="Handles Google OAuth code exchange, verifies identity, creates or links account, and returns JWT.",
)
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None, description="Optional CSRF state parameter"),
    db: Session = Depends(get_db),
):
    try:
        user_info = await google_oauth_service.exchange_code_for_user_info(code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}",
        )

    user, token = auth_service.handle_google_callback_user(db, user_info)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Forgot Password",
    description="Sends a password reset link to the email if registered, protected against email enumeration.",
)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    message = auth_service.forgot_password(db, request.email)
    return MessageResponse(message=message)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset Password",
    description="Resets the user's password using the single-use token from Redis, re-hashing with Argon2id.",
)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, request.token, request.new_password)
    return MessageResponse(
        message="Password has been reset successfully. You can now log in with your new password."
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Revokes the current JWT access token by blacklisting it in Redis.",
)
def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    current_user: User = Depends(get_current_user),
):
    if credentials:
        auth_service.logout_user(credentials.credentials)
    return MessageResponse(message="Successfully logged out.")
