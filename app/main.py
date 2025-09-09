from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.websocket.routes import register_ws_routes

app = FastAPI(title="Scholar Backend", version="1.0.0")

# CORS — tighten in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.get("/health")
def health():
    return {"status": "ok"}

# mount the websocket endpoint(s) from app/websocket/
register_ws_routes(app)
