"""
Email Channel Sender
====================
Sends transactional emails via Brevo Transactional Email REST API v3.
This uses the v3 API key (BREVO_API_KEY) — no SMTP setup required.

Required env vars (set in .env):
    BREVO_API_KEY    – v3 API key from Brevo → Account → SMTP & API → API Keys
                       Starts with: xsmtpsib-...
    SMTP_FROM_EMAIL  – verified sender email in your Brevo account
                       (must be verified under Senders & IPs in Brevo)

Fallback: if BREVO_API_KEY or SMTP_FROM_EMAIL is missing, the sender
automatically uses mock mode (logs to console, no real email sent).

Brevo free tier: 300 emails/day, no credit card required.
API docs: https://developers.brevo.com/reference/sendtransacemail
"""

import os
from backend.services.channels.base import BaseChannel, ChannelResult

_BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailChannel(BaseChannel):

    channel_name = "Email"

    def __init__(self):
        self._api_key    = os.getenv("BREVO_API_KEY",   "").strip()
        self._from_email = os.getenv("SMTP_FROM_EMAIL", "").strip()
        self._from_name  = os.getenv("SMTP_FROM_NAME",  "Collections Intelligence Bank").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._from_email)

    def send(
        self,
        recipient : str,
        message   : str,
        subject   : str | None = None,
    ) -> ChannelResult:
        """
        Send a transactional email via Brevo REST API v3.
        Falls back to mock mode if credentials are not configured.

        Args:
            recipient : customer email address
            message   : email body (plain text)
            subject   : email subject line
        """
        if not self.is_configured:
            return self._mock_send(recipient, message, subject)

        subject = subject or "Important Notice from Your Bank"

        try:
            import httpx

            headers = {
                "accept"      : "application/json",
                "content-type": "application/json",
                "api-key"     : self._api_key,
            }
            payload = {
                "sender"     : {"name": self._from_name, "email": self._from_email},
                "to"         : [{"email": recipient}],
                "subject"    : subject,
                "textContent": message,
            }

            response = httpx.post(_BREVO_API_URL, json=payload, headers=headers, timeout=15)
            data     = response.json()

            if response.status_code in (200, 201) and "messageId" in data:
                return ChannelResult(
                    success  = True,
                    status   = "sent",
                    message  = f"Email delivered to {recipient} via Brevo. ID: {data['messageId']}",
                    provider = "brevo_api",
                )
            else:
                error_msg = data.get("message", str(data))
                return ChannelResult(
                    success  = False,
                    status   = "failed",
                    message  = f"Brevo API error: {error_msg}",
                    error    = error_msg,
                    provider = "brevo_api",
                )

        except ImportError:
            return self._mock_send(recipient, message, subject)

        except Exception as exc:
            return ChannelResult(
                success  = False,
                status   = "failed",
                message  = f"Email send failed: {str(exc)}",
                error    = str(exc),
                provider = "brevo_api",
            )
