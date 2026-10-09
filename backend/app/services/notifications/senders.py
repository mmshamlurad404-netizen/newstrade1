import asyncio

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("notifications.senders")

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


class LogSender:
    """Default sender: records the notification without external delivery.

    Used for local development and whenever FCM is not configured.
    """

    name = "log"

    async def send(self, token: str, title: str, body: str | None, data=None) -> bool:
        log.info(
            "notify[%s] token=%.8s title=%r" % (self.name, token, title),
            extra={"stage": "notifications"},
        )
        return True


class FcmSender:
    """Firebase Cloud Messaging HTTP v1 sender.

    Only used when ``fcm_project_id`` and ``fcm_credentials_path`` are set.
    Requires the optional ``google-auth`` dependency; if it is missing the
    sender degrades to a no-op and reports failure rather than raising.
    """

    name = "fcm"

    def __init__(self, project_id: str, credentials_path: str) -> None:
        self.project_id = project_id
        self.credentials_path = credentials_path
        self._credentials = None

    def _load_credentials(self):
        if self._credentials is not None:
            return self._credentials
        from google.oauth2 import service_account

        self._credentials = service_account.Credentials.from_service_account_file(
            self.credentials_path, scopes=[FCM_SCOPE]
        )
        return self._credentials

    def _access_token(self) -> str:
        from google.auth.transport.requests import Request

        credentials = self._load_credentials()
        credentials.refresh(Request())
        return credentials.token

    async def send(self, token: str, title: str, body: str | None, data=None) -> bool:
        try:
            access = await asyncio.to_thread(self._access_token)
        except Exception as exc:
            log.error(
                "FCM auth failed: %s" % exc, extra={"stage": "notifications"}
            )
            return False

        url = (
            f"https://fcm.googleapis.com/v1/projects/{self.project_id}"
            "/messages:send"
        )
        message = {
            "message": {
                "token": token,
                "notification": {"title": title, "body": body or ""},
                "data": {k: str(v) for k, v in (data or {}).items() if v is not None},
            }
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json=message,
                    headers={"Authorization": f"Bearer {access}"},
                )
            if response.status_code >= 400:
                log.error(
                    "FCM send failed (%s): %s"
                    % (response.status_code, response.text[:200]),
                    extra={"stage": "notifications"},
                )
                return False
            return True
        except Exception as exc:
            log.error(
                "FCM send error: %s" % exc, extra={"stage": "notifications"}
            )
            return False


def get_sender():
    if settings.fcm_project_id and settings.fcm_credentials_path:
        return FcmSender(settings.fcm_project_id, settings.fcm_credentials_path)
    return LogSender()
