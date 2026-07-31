import asyncio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

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
            logger.debug("RESEND_API_KEY not configured, skipping email to %s", to)
            return None

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
            logger.error("Timeout sending email to %s", to)
            return None
        logger.info("Email sent to %s: %s", to, result.get("id", "unknown"))
        return result

