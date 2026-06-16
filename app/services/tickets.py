"""Client for the ticket microservice.

Single endpoint: POST {TICKET_SERVICE}/bot/tickets with a payload whose `action`
selects the operation (create / email / get). We only need ticket_id and the
rendered PNG (decoded from image_base64) back.
"""
import base64
import json
from dataclasses import dataclass

import httpx
import structlog

from app.helpers.hmac_auth import sign_request

log = structlog.get_logger()

ENDPOINT = "/bot/tickets"


class TicketServiceError(Exception):
    """Raised when the ticket microservice fails or returns an unexpected body."""


@dataclass(slots=True)
class Ticket:
    ticket_id: str
    image_png: bytes


class TicketService:
    def __init__(self, base_url: str, client: httpx.AsyncClient, secret: str) -> None:
        self._url = base_url.rstrip("/") + ENDPOINT
        self._client = client
        self._secret = secret

    async def _post(self, payload: dict) -> Ticket:
        # Serialize once: the very bytes we sign are the bytes we send, so the
        # server recomputes the same HMAC over the raw body it receives.
        body = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json", **sign_request(self._secret, body)}
        try:
            response = await self._client.post(self._url, content=body, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("ticket_service_error", action=payload.get("action"), error=str(exc))
            raise TicketServiceError(str(exc)) from exc

        data = response.json()
        try:
            return Ticket(
                ticket_id=data["ticket_id"],
                image_png=base64.b64decode(data["image_base64"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TicketServiceError(f"unexpected response: {exc}") from exc

    async def create(self, *, name: str | None, prefix: str) -> Ticket:
        """Mint a new paid ticket, returned in chat."""
        return await self._post({"action": "create", "name": name, "prefix": prefix})

    async def email(
        self, *, email: str, name: str | None, prefix: str, lang: str
    ) -> Ticket:
        """Mint a new ticket and email it; also returns the image for the chat."""
        return await self._post(
            {
                "action": "email",
                "email": email,
                "name": name,
                "prefix": prefix,
                "lang": lang,
            }
        )

    async def get(self, *, code: str) -> Ticket:
        """Fetch an existing ticket by its ticket_id."""
        return await self._post({"action": "get", "code": code})
