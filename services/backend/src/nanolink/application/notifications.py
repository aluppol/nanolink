from nanolink.domain.notifications import email_for
from nanolink.domain.ports import EmailSender
from nanolink.domain.tasks import TaskResult


class CreatorNotifications:
    def __init__(self, email: EmailSender, public_base_url: str) -> None:
        self._email = email
        self._public_base_url = public_base_url

    async def notify(self, result: TaskResult) -> None:
        message = email_for(result, self._public_base_url)
        if message is not None:
            await self._email.send(message)
