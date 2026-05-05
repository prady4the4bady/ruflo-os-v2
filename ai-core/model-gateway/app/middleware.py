"""HTTP middleware for the model-gateway.

CorrelationIDMiddleware
-----------------------
Reads ``X-Correlation-ID`` from inbound requests.  If absent, generates a
UUID4.  The resolved ID is:

* stored in ``request.state.correlation_id``
* echoed back in the ``X-Correlation-ID`` response header
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Ensure every request carries a correlation ID."""

    HEADER = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        correlation_id = request.headers.get(self.HEADER) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        response: Response = await call_next(request)
        response.headers[self.HEADER] = correlation_id
        return response
