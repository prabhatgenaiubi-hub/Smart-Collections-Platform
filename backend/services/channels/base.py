"""
Base Channel Abstraction
========================
Abstract base class that every channel sender must implement.
Adding a new channel in future = create a subclass of BaseChannel.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ChannelResult:
    """
    Standardised result returned by every channel sender.
    status: 'sent' | 'mock_sent' | 'failed'
    """
    success    : bool
    status     : str            # 'sent' | 'mock_sent' | 'failed'
    message    : str            # human-readable description
    error      : Optional[str] = None   # error detail when status == 'failed'
    provider   : str = "unknown"        # e.g. 'meta_whatsapp' | 'smtp' | 'brevo' | 'mock'


class BaseChannel(ABC):
    """
    Abstract base for all outreach channel senders.

    Concrete implementations:
      - WhatsAppChannel  (backend/services/channels/whatsapp.py)
      - EmailChannel     (backend/services/channels/email.py)

    Future additions (drop-in):
      - SMSChannel
      - VoiceChannel
    """

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Human-readable channel name, e.g. 'WhatsApp' or 'Email'."""
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """
        Return True if the required environment variables are set.
        If False, the sender will fall back to mock mode automatically.
        """
        ...

    @abstractmethod
    def send(
        self,
        recipient : str,
        message   : str,
        subject   : str | None = None,
    ) -> ChannelResult:
        """
        Send a message to the recipient.

        Args:
            recipient : phone number (WhatsApp) or email address
            message   : body text to send
            subject   : optional subject line (used only by email)

        Returns:
            ChannelResult with success/status/message/error
        """
        ...

    # ── Shared mock helper ────────────────────────────────────────────────────
    def _mock_send(self, recipient: str, message: str, subject: str | None) -> ChannelResult:
        """
        Log-only mock delivery used when real credentials are not configured.
        No real message is sent; just prints to console and returns mock_sent.
        """
        print(f"\n[MOCK {self.channel_name.upper()}] ── MOCK DELIVERY ───────────────────")
        if subject:
            print(f"  Subject : {subject}")
        print(f"  To      : {recipient}")
        print(f"  Body    :\n{message}")
        print(f"────────────────────────────────────────────────────────────────────\n")

        return ChannelResult(
            success  = True,
            status   = "mock_sent",
            message  = (
                f"Mock {self.channel_name} sent to {recipient}. "
                f"Add credentials to send for real."
            ),
            provider = "mock",
        )
