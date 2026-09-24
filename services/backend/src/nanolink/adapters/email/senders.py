import asyncio
import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage

from nanolink.domain.errors import DependencyUnavailable
from nanolink.domain.notifications import EmailMessage

SMTP_TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SmtpSettings:
    host: str
    port: int
    username: str
    password: str
    sender: str


class SmtpEmailSender:
    def __init__(self, settings: SmtpSettings) -> None:
        self._settings = settings

    async def send(self, message: EmailMessage) -> None:
        try:
            await asyncio.to_thread(self._deliver, message)
        except (smtplib.SMTPException, OSError) as error:
            raise DependencyUnavailable from error

    def _deliver(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = self._settings.sender
        mime["To"] = message.recipient
        mime["Subject"] = message.subject
        mime.set_content(message.body)
        with smtplib.SMTP(self._settings.host, self._settings.port, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if self._settings.username:
                smtp.login(self._settings.username, self._settings.password)
            smtp.send_message(mime)


class DisabledEmailSender:
    async def send(self, message: EmailMessage) -> None:
        logger.debug("e-mail delivery is not configured; skipped '%s'", message.subject)
