# Nerodivine WebSocket API

## Endpoint
`ws://localhost:8000/nerodivine/ws/queries`

## Message Flow

### 1. Connection Established
**Server sends:**
```json
{
  "type": "connected",
  "message": "Connected to Nerodivine. Send a 'ready' message with your name to begin."
}
```

### 2. Client Ready (Required)
**Client sends:**
```json
{
  "type": "ready",
  "name": "ChildName"
}
```

### 3. Session Initialized
**Server sends:**
```json
{
  "type": "session_initialized",
  "session_id": "uuid-string"
}
```

### 4. Audio Streaming Begins
**Server sends:**
```json
{
  "type": "audio_start",
  "message": "Starting story for ChildName",
  "encoding": "opus",
  "sample_rate": 22050,
  "channels": 1
}
```

### 5. Audio Chunks
**Server sends binary data:** Opus-encoded audio chunks

### 6. Streaming Complete
**Server sends:**
```json
{
  "type": "end",
  "message": "Story completed"
}
```

## Error Handling
**Server sends on error:**
```json
{
  "type": "error",
  "message": "Error description"
}
```

## Requirements
- `ELEVEN_LABS_API_KEY` environment variable
- `ELEVEN_LABS_VOICE_ID` environment variable (optional, defaults to Hindi voice)
- `opuslib` Python package for audio encoding