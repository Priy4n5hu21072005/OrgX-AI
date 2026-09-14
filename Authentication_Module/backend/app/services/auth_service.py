import logging
from typing import Tuple, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core import security
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest
from app.services.redis_service import redis_service
from app.services.email_service import email_service
from app.utils.tokens import generate_otp, generate_reset_token

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    def register_user(db: Session, request: RegisterRequest) -> Tuple[User, str]:
        """Register a new user, hash password using Argon2id, create OTP, and send email."""
        email_normalized = request.email.lower().strip()

        # Check duplicate email
        existing_user = db.query(User).filter(User.email == email_normalized).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )

        # Hash password with Argon2id
        hashed_password = security.hash_password(request.password)

        # Create user record (unverified by default)
        user = User(
            name=request.name.strip(),
            email=email_normalized,
            password_hash=hashed_password,
            auth_provider="local",
            is_email_verified=False,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Generate OTP, store in Redis, send verification email
        otp = generate_otp(length=6)
        redis_service.set_email_otp(email_normalized, otp)
        email_service.send_verification_email(email_normalized, otp)

        return user, otp

    @staticmethod
    def verify_email(db: Session, email: str, otp: str) -> User:
        """Verify user's email with the 6-digit OTP stored in Redis."""
        email_normalized = email.lower().strip()
        stored_otp = redis_service.get_email_otp(email_normalized)

        if not stored_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code is invalid or has expired",
            )

        if stored_otp != otp.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code",
            )

        user = db.query(User).filter(User.email == email_normalized).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user.is_email_verified = True
        db.commit()
        db.refresh(user)

        # Clean up Redis key
        redis_service.delete_email_otp(email_normalized)

        # Send welcome email
        email_service.send_welcome_email(user.email, user.name)

        return user

    @staticmethod
    def resend_verification_otp(db: Session, email: str) -> None:
        """Resend OTP for unverified email."""
        email_normalized = email.lower().strip()
        user = db.query(User).filter(User.email == email_normalized).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified",
            )

        otp = generate_otp(length=6)
        redis_service.set_email_otp(email_normalized, otp)
        email_service.send_verification_email(email_normalized, otp)

    @staticmethod
    def login_user(db: Session, request: LoginRequest) -> Tuple[User, str]:
        """Authenticate user by email and password, returning JWT access token."""
        email_normalized = request.email.lower().strip()
        user = db.query(User).filter(User.email == email_normalized).first()

        # Constant time or uniform error response
        if not user or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not security.verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact support.",
            )

        if not user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email is not verified. Please verify your email before logging in.",
            )

        token = security.create_access_token(subject=user.id)
        return user, token

    @staticmethod
    def forgot_password(db: Session, email: str) -> str:
        """Generate password reset token and email it without disclosing account existence."""
        email_normalized = email.lower().strip()
        user = db.query(User).filter(User.email == email_normalized).first()

        if user and user.is_active:
            reset_token = generate_reset_token()
            redis_service.set_reset_token(reset_token, user.id)
            email_service.send_password_reset_email(user.email, reset_token)

        # Uniform message to prevent email enumeration
        return "If an account exists for this email, a password reset link has been sent."

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> None:
        """Reset password using one-time token from Redis and update hash with Argon2id."""
        user_id = redis_service.get_reset_token_user_id(token)

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset link is invalid or has expired",
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Hash new password with Argon2id
        user.password_hash = security.hash_password(new_password)
        # Email verified since reset was clicked from their inbox
        user.is_email_verified = True
        db.commit()

        # Delete token to guarantee single-use
        redis_service.delete_reset_token(token)

    @staticmethod
    def handle_google_callback_user(db: Session, google_user_info: Dict[str, Any]) -> Tuple[User, str]:
        """Find or create user from Google profile and issue JWT."""
        google_id = google_user_info.get("sub")
        email = google_user_info.get("email", "").lower().strip()
        name = google_user_info.get("name") or email.split("@")[0]

        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incomplete Google user profile received",
            )

        # Check if user exists by google_id or email
        user = db.query(User).filter(
            (User.google_id == google_id) | (User.email == email)
        ).first()

        if user:
            # Link Google account if not linked yet
            if not user.google_id:
                user.google_id = google_id
            user.is_email_verified = True
            db.commit()
            db.refresh(user)
        else:
            # Create new user via Google
            user = User(
                name=name,
                email=email,
                password_hash=None,
                auth_provider="google",
                google_id=google_id,
                is_email_verified=True,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        token = security.create_access_token(subject=user.id)
        return user, token

    @staticmethod
    def logout_user(token: str) -> None:
        """Revoke token by storing jti/token in Redis blacklist."""
        payload = security.decode_access_token(token)
        if payload:
            jti = payload.get("jti") or token
            redis_service.blacklist_token(jti, ttl=3600)
        else:
            redis_service.blacklist_token(token, ttl=3600)


auth_service = AuthService()
