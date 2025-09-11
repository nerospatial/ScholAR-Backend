from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os

from app.websocket.routes import register_ws_routes
from app.controllers.google_auth_controller import router
app = FastAPI(title="Scholar Backend", version="1.0.0")

# CORS — tighten in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
    
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET_KEY", "your_default_secret")
)


@app.get("/health")
def health():
    return {"status": "ok"}

# mount the websocket endpoint(s) from app/websocket/
register_ws_routes(app)

app.include_router(router, prefix="/api/v1")
