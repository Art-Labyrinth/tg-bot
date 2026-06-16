"""HMAC signing for trusted server-to-server requests.

We share a secret (``BOT_API_SECRET``) with a bot-facing API and sign every
request body. Two headers are sent:

    X-Bot-Timestamp: <unix seconds>
    X-Bot-Signature: hex( HMAC_SHA256(secret, f"{timestamp}.{raw_body}") )

The signature covers the EXACT bytes of the request body, so the caller must
sign and send the same serialized bytes: serialize once, then pass those bytes
both to ``sign_request`` and to the HTTP client (httpx ``content=``).

Cross-cutting auth — lives in helpers/ so any bot-facing client can reuse it; it
must not import a service.
"""
import hashlib
import hmac
import time

TIMESTAMP_HEADER = "X-Bot-Timestamp"
SIGNATURE_HEADER = "X-Bot-Signature"


def sign_request(
    secret: str, body: bytes, *, timestamp: int | None = None
) -> dict[str, str]:
    """Build the HMAC auth headers for a raw request body.

    ``body`` must be the exact bytes that will be sent. ``timestamp`` is only for
    tests; by default the current unix time is used.
    """
    ts = int(time.time()) if timestamp is None else timestamp
    message = f"{ts}.".encode() + body
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return {TIMESTAMP_HEADER: str(ts), SIGNATURE_HEADER: signature}
