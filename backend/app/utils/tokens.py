import secrets
import string


def generate_otp(length: int = 6) -> str:
    """Generate a cryptographically secure random numeric OTP."""
    digits = string.digits
    return "".join(secrets.choice(digits) for _ in range(length))


def generate_reset_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure, URL-safe random reset token."""
    return secrets.token_urlsafe(nbytes)
