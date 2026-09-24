from dataclasses import dataclass

from nanolink.domain.links import short_url_for
from nanolink.domain.tasks import TaskResult, TaskStatus


@dataclass(frozen=True, slots=True)
class EmailMessage:
    recipient: str
    subject: str
    body: str


def email_for(result: TaskResult, public_base_url: str) -> EmailMessage | None:
    if result.notify_email is None:
        return None
    link = result.report.link
    if result.report.status is TaskStatus.CREATED and link is not None:
        short_url = short_url_for(public_base_url, link.short_code)
        body = f"Your short link is ready: {short_url}\nIt redirects to: {link.long_url}\n"
        return EmailMessage(result.notify_email, "Your NanoLink is ready", body)
    body = f"NanoLink could not create your link: {result.report.failure}\n"
    return EmailMessage(result.notify_email, "NanoLink could not create your link", body)
