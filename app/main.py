import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.db.database import Base, engine
from app.websocket.routes import register_ws_routes
from app.api.v1.endpoints.google_auth import router as google_auth_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.me import router as me_router
from app.api.v1.endpoints.device_auth import router as device_auth_router
from dotenv import load_dotenv
from app.models import hardware

load_dotenv()

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

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

# mount the websocket endpoint(s) from app/websocket/
register_ws_routes(app)


app.include_router(google_auth_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")

app.include_router(device_auth_router, prefix="/api/v1")