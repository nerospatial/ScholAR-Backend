# ScholAR Pi → Backend WebSocket API Documentation

This document defines how **ScholAR Pi firmware** connects to the ScholAR backend, streams **audio + video**, and receives **real-time responses** from Gemini via the server.

The API is WebSocket-based and designed for **low-latency audio tutoring with optional camera frames**.

---

## 1. WebSocket Endpoint

```
ws://<BACKEND_HOST>:8080/ws/queries
```

* Transport: **WebSocket** (persistent connection)
* Protocol: JSON messages

---

## 2. Session Lifecycle

Each interaction follows the same lifecycle:

1. **Connect**

   * Open a WebSocket to `/ws/queries`.
   * Backend responds immediately:

     ```json
     { "type": "READY" }
     ```

2. **Start a Session**

   * Client must explicitly request session start:

     ```json
     { "type": "START_QUERY_SESSION" }
     ```
   * Server confirms with:

     ```json
     { "type": "START_QUERY_SESSION" }
     ```

3. **Stream Input**

   * Audio chunks (mic input)
   * Video frames (camera stills, optional)
   * Text queries (optional)

4. **Receive Output**

   * Real-time audio stream (speech)
   * Optional text responses (transcripts or model outputs)
   * Control events (speaking/done)

5. **Interrupt (optional)**

   * Client may cancel mid-turn:

     ```json
     { "type": "USER_INTERRUPTED" }
     ```

6. **Stop Session**

   * When finished:

     ```json
     { "type": "STOP_QUERY_SESSION" }
     ```
   * Server closes Gemini session:

     ```json
     { "type": "SESSION_ENDED" }
     ```

7. **Disconnect**

   * Close the WebSocket normally.

---

## 3. Message Formats

### 3.1 Audio Input → Server

* Format: PCM16LE, 16 kHz, mono
* Chunks: ~10–60 ms each (320–1024 samples)
* Encoding: Base64

```json
{
  "type": "audio",
  "data": "<base64_pcm16_chunk>",
  "sample_rate": 16000
}
```

---

### 3.2 Video Frame Input → Server

* Format: JPEG
* Size: ≤ 1024×1024
* Interval: ~1 fps recommended
* Encoding: Base64

```json
{
  "type": "video",
  "data": "<base64_jpeg_bytes>",
  "mime_type": "image/jpeg"
}
```

---

### 3.3 Text Input → Server

```json
{
  "type": "text",
  "data": "What do you see in this frame?"
}
```

---

### 3.4 Audio Response ← Server

* Format: PCM16LE, 24 kHz, mono
* Must be queued and played in **strict order**

```json
{
  "type": "audio_response",
  "data": "<base64_pcm16_chunk>",
  "sample_rate": 24000,
  "encoding": "pcm_s16le",
  "channels": 1
}
```

---

### 3.5 Text Response ← Server

```json
{
  "type": "text_response",
  "data": "It looks like a laptop on a desk."
}
```

---

### 3.6 Control Events ← Server

* Speaking started:

  ```json
  { "type": "QUERY_RESPONDER_SPEAKING" }
  ```
* Speaking finished:

  ```json
  { "type": "QUERY_RESPONDER_DONE" }
  ```
* Session ended:

  ```json
  { "type": "SESSION_ENDED" }
  ```
* Error:

  ```json
  { "type": "ERROR", "message": "Invalid audio data" }
  ```

---

## 4. Audio/Video Specs

### Input (Mic → Server)

* PCM16LE
* 16 kHz
* Mono
* Base64 chunks

### Output (Server → Client)

* PCM16LE
* 24 kHz
* Mono
* Base64 chunks

### Camera Frames

* JPEG, base64
* ≤ 1024×1024
* ~1 fps

---

## 5. Implementation Checklist (ScholAR Pi)

* [ ] Connect WebSocket and wait for `READY`.
* [ ] Send `START_QUERY_SESSION`.
* [ ] Encode mic audio as **PCM16LE, 16 kHz**.
* [ ] Send chunks regularly (~20–40 ms).
* [ ] Encode camera frames as **JPEG base64** and send at ~1 fps.
* [ ] Handle `audio_response` → decode base64 → play FIFO at **24 kHz**.
* [ ] Handle `text_response` if present (optional logging).
* [ ] Handle `QUERY_RESPONDER_SPEAKING` / `DONE` events.
* [ ] On user cancel: send `USER_INTERRUPTED`.
* [ ] On session end: send `STOP_QUERY_SESSION` → expect `SESSION_ENDED`.
* [ ] Close WebSocket cleanly.

---

## 6. Minimal Python Snippet (Pi)

```python
import base64, asyncio, websockets

async def main():
    uri = "ws://localhost:8080/ws/queries"
    async with websockets.connect(uri) as ws:
        # Wait for READY
        print(await ws.recv())

        # Start session
        await ws.send('{"type":"START_QUERY_SESSION"}')

        # Example: send audio
        pcm_chunk = b"\x00\x01..."  # raw PCM16LE
        b64 = base64.b64encode(pcm_chunk).decode()
        await ws.send(f'{{"type":"audio","data":"{b64}","sample_rate":16000}}')

        # Read responses
        while True:
            msg = await ws.recv()
            print(msg)

asyncio.run(main())
```

---

## 7. Error Handling

* Always check for `{ "type": "ERROR", "message": "..." }`.
* If unrecoverable, stop session and reconnect.
* If recoverable (e.g., bad frame), log and continue.
