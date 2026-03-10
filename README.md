# ScholAR Backend

Backend server for ScholAR: AR glasses that see what you see, hear what you say, and responds in realtime.

Camera frames and audio from the glasses are streamed here over WebSocket. A multimodal LLM (currently Gemini) processes both in real time and streams spoken responses back to the glasses.

---

## What It Does

- Accepts a live WebSocket connection from the AR glasses
- Receives **audio chunks** (base64 PCM) and **video frames** (base64 JPEG) from the device
- Feeds them into **Gemini Live** for real-time multimodal understanding
- Streams **text + audio responses** back to the glasses as they're generated
- Handles user auth (email/password + Google OAuth), device registration, and session management

---


## Project Structure

```
   app/
   ├── main.py               - App entry, middleware, route registration
   ├── api/v1/endpoints/     - REST route handlers
   ├── websocket/
   │   ├── routes.py         - WebSocket handler + session manager
   │   └── helpers/          - Message builders
   ├── llm/
   │   ├── interfaces/       - Abstract LLM provider
   │   └── providers/gemini/ - Gemini Live implementation
   ├── services/             - Business logic (auth, devices, stories)
   ├── models/               - SQLAlchemy ORM models
   ├── schemas/              - Pydantic request/response schemas
   ├── core/                 - Config, logging
   └── db/                   - DB engine + session
   ```


## Architecture

```
   AR Glasses
   │
   │  WebSocket (/ws/queries)
   ▼
   Server
   |
   ├── WebSocketSession           - per-connection state manager
   │     ├── send_audio()         - PCM chunks → Gemini
   │     ├── send_video()         - JPEG frames → Gemini
   │     └── send_text()          - optional text input
   │
   ├── LLM Provider (Gemini)     
   │     ├── get_audio_response() - streamed PCM back to glasses
   │     └── get_text_response()  - streamed text back to glasses
   │
   ├── REST API (/api/v1)
   │     ├── /auth                - register, login, JWT
   │     ├── /auth/google         - Google OAuth
   │     ├── /device-auth         - hardware device registration
   │     ├── /me                  - user profile
   │     └── /toys/stories        - story content + TTS playback
   │
   └── PostgreSQL (SQLAlchemy)
         ├── users
         ├── devices
         └── stories
```

---

## Tech Stack

| Layer | Tech |
|---|---|
| Framework | FastAPI + Uvicorn |
| Realtime | WebSockets (native FastAPI) |
| LLM | Google Gemini Live (multimodal) |
| TTS (stories) | ElevenLabs |
| Database | PostgreSQL + SQLAlchemy |
| Auth | JWT + Google OAuth (Authlib) |
| Config | Pydantic Settings + `.env` |
| Container | Docker + Docker Compose |

---

## Realtime Messaging

Connect to `ws://<host>/ws/queries`

```
   Glasses → Server
   │
   ├── START_QUERY_SESSION       - opens LLM session
   ├── audio                     - { data: base64_pcm, sample_rate: 16000 }
   ├── video                     - { data: base64_jpeg, mime_type: "image/jpeg" }
   ├── text                      - { data: "..." }
   ├── USER_INTERRUPTED          - signals user cut off response
   └── STOP_QUERY_SESSION        - ends session cleanly

   Server → Glasses
   │
   ├── READY                     - connection accepted
   ├── START_QUERY_SESSION       - LLM session active
   ├── QUERY_RESPONDER_SPEAKING  - audio stream starting
   ├── audio_response            - { data: base64_pcm, sample_rate: 24000, encoding: "pcm_s16le" }
   ├── text_response             - { data: "..." }
   ├── QUERY_RESPONDER_DONE      - response complete
   ├── SESSION_ENDED             - session closed
   └── error                    - { message: "..." }
```

---


## Running Locally

**Prerequisites:** Python 3.10+, PostgreSQL, a `.env` file (see `.env.example`)

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000
```

**With Docker:**

```bash
docker compose up --build
```

---

## Environment Variables

```env
DATABASE_URL=postgresql://user:password@localhost:5432/scholar
SECRET_KEY=your_jwt_secret
SESSION_SECRET_KEY=your_session_secret
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GEMINI_API_KEY=...
ELEVENLABS_API_KEY=...
```

---
