import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self) -> None:
        # Record of sent emails for local testing/debugging
        self.sent_emails: List[Dict[str, Any]] = []

    def _send_email(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
        """Internal helper to dispatch email via SMTP or record in mock mode."""
        email_record = {
            "to": to_email,
            "subject": subject,
            "body": body_text,
            "html": body_html,
        }
        self.sent_emails.append(email_record)

        if settings.EMAIL_MOCK_MODE or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.info("=" * 60)
            logger.info("[MOCK EMAIL] TO: %s", to_email)
            logger.info("[MOCK EMAIL] SUBJECT: %s", subject)
            logger.info("[MOCK EMAIL] BODY:\n%s", body_text)
            logger.info("=" * 60)
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = to_email

            part1 = MIMEText(body_text, "plain")
            msg.attach(part1)
            if body_html:
                part2 = MIMEText(body_html, "html")
                msg.attach(part2)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

            logger.info("Email sent successfully to %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, e)
            return False

    def send_verification_email(self, to_email: str, otp: str) -> bool:
        """Send 6-digit OTP verification code."""
        subject = "Verify your OrgX-AI account"
        body = (
            f"Welcome to OrgX-AI!\n\n"
            f"Please verify your email to activate your account.\n\n"
            f"Your verification code:\n{otp}\n\n"
            f"This code will expire in {settings.REDIS_OTP_EXPIRE_SECONDS // 60} minutes.\n"
            f"If you did not create an OrgX-AI account, you can ignore this email."
        )
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h2 style="color: #2563eb;">Welcome to OrgX-AI!</h2>
            <p>Please verify your email to activate your account.</p>
            <div style="background-color: #f3f4f6; padding: 16px; border-radius: 6px; text-align: center; margin: 20px 0;">
                <span style="font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #111827;">{otp}</span>
            </div>
            <p style="color: #6b7280; font-size: 14px;">This code will expire in {settings.REDIS_OTP_EXPIRE_SECONDS // 60} minutes.</p>
            <p style="color: #9ca3af; font-size: 12px;">If you did not request this, please ignore this email.</p>
        </div>
        """
        return self._send_email(to_email, subject, body, html)

    def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        """Send password reset link."""
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        subject = "Reset your OrgX-AI password"
        body = (
            f"We received a request to reset your password.\n\n"
            f"Click the link below:\n\n"
            f"{reset_url}\n\n"
            f"This link expires in {settings.REDIS_RESET_TOKEN_EXPIRE_SECONDS // 60} minutes.\n\n"
            f"If you did not request this, ignore this email."
        )
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h2 style="color: #2563eb;">Reset your OrgX-AI password</h2>
            <p>We received a request to reset your password.</p>
            <div style="margin: 24px 0;">
                <a href="{reset_url}" style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                    Reset Password
                </a>
            </div>
            <p style="color: #6b7280; font-size: 14px;">Or paste this link in your browser: <br><a href="{reset_url}">{reset_url}</a></p>
            <p style="color: #6b7280; font-size: 14px;">This link expires in {settings.REDIS_RESET_TOKEN_EXPIRE_SECONDS // 60} minutes.</p>
            <p style="color: #9ca3af; font-size: 12px;">If you did not request this, ignore this email.</p>
        </div>
        """
        return self._send_email(to_email, subject, body, html)

    def send_welcome_email(self, to_email: str, name: str) -> bool:
        """Send welcome confirmation email after activation."""
        subject = "Welcome to OrgX-AI!"
        body = f"Hi {name},\n\nYour OrgX-AI account has been successfully verified! You can now log in."
        return self._send_email(to_email, subject, body)


email_service = EmailService()
