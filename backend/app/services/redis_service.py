import logging
import time
from typing import Optional, Dict, Tuple
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class InMemoryStore:
    """Fallback in-memory key-value store with TTL support for development/testing."""

    def __init__(self) -> None:
        self._data: Dict[str, Tuple[str, Optional[float]]] = {}

    def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        expire_at = time.time() + ex if ex else None
        self._data[key] = (value, expire_at)

    def get(self, key: str) -> Optional[str]:
        if key not in self._data:
            return None
        val, expire_at = self._data[key]
        if expire_at and time.time() > expire_at:
            del self._data[key]
            return None
        return val

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def flush(self) -> None:
        self._data.clear()


class RedisService:
    def __init__(self) -> None:
        self._memory_store = InMemoryStore()
        self._redis_client: Optional[redis.Redis] = None
        self._use_fallback = False

        try:
            client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
            )
            # Test ping
            client.ping()
            self._redis_client = client
            logger.info("Successfully connected to Redis at %s", settings.REDIS_URL)
        except Exception as e:
            logger.warning(
                "Could not connect to Redis (%s). Using in-memory fallback store for local development.",
                e,
            )
            self._use_fallback = True

    def _set_value(self, key: str, value: str, ex: int) -> None:
        if not self._use_fallback and self._redis_client:
            try:
                self._redis_client.set(key, value, ex=ex)
                return
            except Exception as e:
                logger.warning("Redis operation failed (%s). Falling back to in-memory store.", e)
        self._memory_store.set(key, value, ex=ex)

    def _get_value(self, key: str) -> Optional[str]:
        if not self._use_fallback and self._redis_client:
            try:
                return self._redis_client.get(key)
            except Exception as e:
                logger.warning("Redis get failed (%s). Falling back to in-memory store.", e)
        return self._memory_store.get(key)

    def _delete_value(self, key: str) -> None:
        if not self._use_fallback and self._redis_client:
            try:
                self._redis_client.delete(key)
                return
            except Exception as e:
                logger.warning("Redis delete failed (%s). Falling back to in-memory store.", e)
        self._memory_store.delete(key)

    # 1. Email verification OTP
    def set_email_otp(self, email: str, otp: str, ttl: int = settings.REDIS_OTP_EXPIRE_SECONDS) -> None:
        key = f"email_verification:{email.lower()}"
        self._set_value(key, otp, ex=ttl)

    def get_email_otp(self, email: str) -> Optional[str]:
        key = f"email_verification:{email.lower()}"
        return self._get_value(key)

    def delete_email_otp(self, email: str) -> None:
        key = f"email_verification:{email.lower()}"
        self._delete_value(key)

    # 2. Forgot password reset token
    def set_reset_token(self, token: str, user_id: int, ttl: int = settings.REDIS_RESET_TOKEN_EXPIRE_SECONDS) -> None:
        key = f"forgot_password:{token}"
        self._set_value(key, str(user_id), ex=ttl)

    def get_reset_token_user_id(self, token: str) -> Optional[int]:
        key = f"forgot_password:{token}"
        val = self._get_value(key)
        return int(val) if val else None

    def delete_reset_token(self, token: str) -> None:
        key = f"forgot_password:{token}"
        self._delete_value(key)

    # 3. Token Blacklist (for Logout)
    def blacklist_token(self, jti_or_token: str, ttl: int = 3600) -> None:
        key = f"blacklisted_token:{jti_or_token}"
        self._set_value(key, "1", ex=ttl)

    def is_token_blacklisted(self, jti_or_token: str) -> bool:
        key = f"blacklisted_token:{jti_or_token}"
        val = self._get_value(key)
        return val is not None

    def clear_all(self) -> None:
        """Clear store (mainly for tests)."""
        self._memory_store.flush()
        if not self._use_fallback and self._redis_client:
            try:
                self._redis_client.flushdb()
            except Exception:
                pass


redis_service = RedisService()
