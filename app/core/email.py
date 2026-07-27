import asyncio

from app.core.config import settings

_RESEND_READY = False


def _init_resend():
    global _RESEND_READY
    if _RESEND_READY:
        return
    if settings.RESEND_API_KEY:
        import resend

        resend.api_key = settings.RESEND_API_KEY
        _RESEND_READY = True


class EmailSender:
    async def send(self, to: str, subject: str, html: str) -> dict | None:
        _init_resend()
        if not _RESEND_READY:
            print(f"[email] RESEND_API_KEY not configured, skipping email to {to}")
            return None

        import resend

        params: resend.Emails.SendParams = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        }

        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, resend.Emails.send, params),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            print(f"[email] Timeout sending to {to}")
            return None
        print(f"[email] Sent to {to}: {result.get('id', 'unknown')}")
        return result


def get_email_sender() -> EmailSender:
    return EmailSender()
