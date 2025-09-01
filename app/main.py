from fastapi import FastAPI
from app.websocket.router import router as ws_router

app = FastAPI(title="Scholar Backend - WS Audio")

# Mount WebSocket routes
app.include_router(ws_router)

# Optional health check (handy for smoke tests)
@app.get("/health")
def health():
    return {"ok": True}
