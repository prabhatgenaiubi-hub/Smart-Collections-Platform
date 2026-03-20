"""
WhatsApp Channel Sender
=======================
Uses Meta WhatsApp Cloud API to send text messages.

Required env vars (set in .env):
    WHATSAPP_ACCESS_TOKEN   – permanent system user token from Meta Business Manager
    WHATSAPP_PHONE_NUMBER_ID – the Phone Number ID shown in WhatsApp > API Setup

If either variable is missing, the sender automatically falls back to mock mode
(logs to console, returns status='mock_sent') so the rest of the app works
without any real credentials during development.

Production notes:
  • Free-tier: Meta gives 1,000 free business-initiated conversations/month per WABA.
  • Message templates must be approved for business-initiated messages.
  • For testing (sandbox), add recipient numbers in Meta's "To" field first.
"""

import os
from backend.services.channels.base import BaseChannel, ChannelResult


_META_API_URL = "https://graph.facebook.com/v19.0/{phone_number_id}/messages"


class WhatsAppChannel(BaseChannel):

    channel_name = "WhatsApp"

    def __init__(self):
        self._access_token    = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
        self._phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self._access_token and self._phone_number_id)

    def send(
        self,
        recipient : str,
        message   : str,
        subject   : str | None = None,   # not used for WhatsApp
    ) -> ChannelResult:
        """
        Send a WhatsApp text message via Meta Cloud API.
        Falls back to mock if credentials are not set.

        Args:
            recipient : customer phone number in international format, e.g. +919876543210
            message   : message body text
            subject   : ignored for WhatsApp
        """
        if not self.is_configured:
            return self._mock_send(recipient, message, subject)

        # ── Real send via Meta Cloud API ─────────────────────────────────────
        try:
            import httpx

            # Ensure E.164 format — Meta requires leading '+' (e.g. +919958270536)
            normalized = recipient.strip()
            if not normalized.startswith("+"):
                normalized = "+" + normalized

            url = _META_API_URL.format(phone_number_id=self._phone_number_id)
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type" : "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type"   : "individual",
                "to"               : normalized,
                "type"             : "text",
                "text"             : {"preview_url": False, "body": message},
            }

            response = httpx.post(url, json=payload, headers=headers, timeout=15)
            data     = response.json()

            if response.status_code == 200 and "messages" in data:
                return ChannelResult(
                    success  = True,
                    status   = "sent",
                    message  = f"WhatsApp message delivered to {recipient}.",
                    provider = "meta_whatsapp",
                )
            else:
                error_msg = data.get("error", {}).get("message", str(data))
                return ChannelResult(
                    success  = False,
                    status   = "failed",
                    message  = f"WhatsApp API error: {error_msg}",
                    error    = error_msg,
                    provider = "meta_whatsapp",
                )

        except ImportError:
            # httpx not installed — degrade gracefully
            return self._mock_send(recipient, message, subject)

        except Exception as exc:
            return ChannelResult(
                success  = False,
                status   = "failed",
                message  = f"WhatsApp send failed: {str(exc)}",
                error    = str(exc),
                provider = "meta_whatsapp",
            )
