from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def send_password_reset_email(
    to_email: str,
    reset_token: str,
    user_name: str = "",
    reset_url: Optional[str] = None,
) -> Dict[str, Any]:
    if not reset_url:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    subject = "Password Reset Request"
    recipient = user_name if user_name else to_email

    email_content = _build_reset_email_content(
        recipient=recipient,
        reset_url=reset_url,
        app_name=settings.APP_NAME,
    )

    result = await _send_email(
        to_email=to_email,
        subject=subject,
        html_content=email_content.get("html", ""),
        text_content=email_content.get("text", ""),
    )

    logger.info(
        "Password reset email %s for %s",
        "sent" if result.get("success") else "not sent",
        to_email,
    )

    return {
        "success": result.get("success", False),
        "to": to_email,
        "subject": subject,
        "reset_url": reset_url,
        "provider": result.get("provider"),
        "message": result.get("message"),
    }


def _build_reset_email_content(
    recipient: str,
    reset_url: str,
    app_name: str,
) -> Dict[str, str]:
    text = f"""Hi {recipient},

You requested a password reset for your {app_name} account.

Click the link below to set a new password:
{reset_url}

This link will expire in 60 minutes.

If you did not request this, please ignore this email.

Best regards,
The {app_name} Team
"""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Password Reset - {app_name}</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Password Reset Request</h2>
        <p>Hi {recipient},</p>
        <p>You requested a password reset for your {app_name} account.</p>
        <p>Click the button below to set a new password:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}"
               style="display: inline-block; padding: 12px 30px; background-color: #3498db;
                      color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
              Reset Password
            </a>
        </div>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #7f8c8d;">{reset_url}</p>
        <p><strong>This link will expire in 60 minutes.</strong></p>
        <p>If you did not request a password reset, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="font-size: 12px; color: #999;">
          Best regards,<br>
          The {app_name} Team
        </p>
    </div>
</body>
</html>"""

    return {"html": html, "text": text}


async def _send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str,
) -> Dict[str, Any]:
    if settings.APP_ENV in ("development", "testing") or settings.DEBUG:
        logger.debug(
            "[DEV MODE] Would send email to=%s subject=%s\n---\n%s",
            to_email,
            subject,
            text_content,
        )
        return {
            "success": True,
            "provider": "console",
            "message": "Email logged to console (dev mode)",
        }

    return {
        "success": False,
        "provider": None,
        "message": "No email provider configured",
    }
