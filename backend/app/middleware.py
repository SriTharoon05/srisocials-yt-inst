from collections import OrderedDict, deque
from time import monotonic
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException


class RequestLimits:
    """Bound multipart input before parsing; per-process login throttling for a single free instance."""
    def __init__(self, app):
        self.app = app
        self.attempts = OrderedDict()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        if path in ("/team/login", "/admin/login") and scope["method"] == "POST":
            key = (scope.get("client") or ("unknown",))[0]
            now = monotonic()
            bucket = self.attempts.setdefault(key, deque())
            self.attempts.move_to_end(key)
            while bucket and bucket[0] < now - 60:
                bucket.popleft()
            if len(bucket) >= 20:
                return await JSONResponse({"detail": "Too many attempts; wait one minute"}, 429)(scope, receive, send)
            bucket.append(now)
            if len(self.attempts) > 2000:
                self.attempts.popitem(last=False)
        limit = 51 * 1024 * 1024 if path == "/public/uploads" else 64 * 1024
        size = 0
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = limit + 1
        if declared > limit:
            return await JSONResponse({"detail": "Request is too large (video limit 50 MB)"}, 413)(scope, receive, send)

        async def bounded_receive():
            nonlocal size
            message = await receive()
            size += len(message.get("body", b""))
            if size > limit:
                raise HTTPException(413, "Request exceeds upload limit")
            return message
        await self.app(scope, bounded_receive, send)
