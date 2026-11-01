class HTTPException(Exception):
    def __init__(self, status_code, detail=None):
        super().__init__(detail); self.status_code, self.detail = status_code, detail
class _R:
    def __init__(self, *a, **k): pass
    def _d(self, *a, **k): return lambda f: f
    get = post = put = delete = websocket = _d
    def include_router(self, *a, **k): pass
APIRouter = _R
def Depends(f=None): return f
class Response:
    def __init__(self, content=b"", media_type=None, headers=None): self.content, self.media_type, self.headers = content, media_type, headers or {}
class Request: pass
class WebSocket: pass
class WebSocketDisconnect(Exception): pass
