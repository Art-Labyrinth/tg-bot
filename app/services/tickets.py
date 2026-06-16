"""Client for the ticket microservice.

Issuance goes through POST {TICKET_SERVICE}/bot/tickets with a payload whose
`action` selects the operation (create / email / get); we get back a ticket_id
and the rendered PNG (decoded from image_base64). A second endpoint,
POST /bot/tickets/stats, returns aggregate sales/usage figures. Both are signed
with the same HMAC scheme.
"""
import base64
import json
from dataclasses import dataclass

import httpx
import structlog

from app.helpers.hmac_auth import sign_request

log = structlog.get_logger()

ENDPOINT = "/bot/tickets"
STATS_ENDPOINT = "/bot/tickets/stats"


class TicketServiceError(Exception):
    """Raised when the ticket microservice fails or returns an unexpected body."""


@dataclass(slots=True)
class Ticket:
    ticket_id: str
    image_png: bytes


class TicketService:
    def __init__(self, base_url: str, client: httpx.AsyncClient, secret: str) -> None:
        self._base = base_url.rstrip("/")
        self._client = client
        self._secret = secret

    async def _request(self, path: str, payload: dict) -> dict:
        """Sign and POST `payload` to `path`, returning the parsed JSON body."""
        # Serialize once: the very bytes we sign are the bytes we send, so the
        # server recomputes the same HMAC over the raw body it receives.
        body = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json", **sign_request(self._secret, body)}
        try:
            response = await self._client.post(
                self._base + path, content=body, headers=headers
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("ticket_service_error", endpoint=path, error=str(exc))
            raise TicketServiceError(str(exc)) from exc
        return response.json()

    async def _post(self, payload: dict) -> Ticket:
        data = await self._request(ENDPOINT, payload)
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

    async def stats(self) -> dict:
        """Fetch aggregate ticket statistics (sales / sold / usage)."""
        return await self._request(STATS_ENDPOINT, {})
