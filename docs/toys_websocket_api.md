# ScholAR Toys → Backend WebSocket API Documentation

This document defines how **ScholAR Toys devices** connect to the ScholAR backend, stream **audio queries**, and receive **real-time responses** from Little Krishna AI via the server.

The API is WebSocket-based and designed for **audio-only interactive conversations** with the Little Krishna AI persona for NeroDivine toys.

---

## 1. WebSocket Endpoints

# ScholAR Toys → Backend WebSocket API Documentation

This document defines how **ScholAR Toys devices** connect to the ScholAR backend, stream **audio queries**, and receive **real-time responses** from Little Krishna AI via the server.

The API is WebSocket-based and designed for **audio-only interactive conversations** with the Little Krishna AI persona for NeroDivine toys.

---

## 1. WebSocket Endpoint

```
ws://<BACKEND_HOST>:8080/ws/toys/queries
```

* Transport: **WebSocket** (persistent connection)
* Protocol: JSON messages
* Purpose: Voice queries and conversations with Little Krishna AI

---

## 2. Session Lifecycle

Each interaction follows the same lifecycle:

1. **Connect**

   * Open a WebSocket to `/ws/toys/queries`.
   * Backend responds immediately:

     ```json
     { "type": "READY" }
     ```

2. **Start Query Session**

   * Client must explicitly request session start:

     ```json
     { "type": "START_QUERY_SESSION" }
     ```
   * Server confirms with:

     ```json
     { "type": "START_QUERY_SESSION" }
     ```

3. **Stream Audio Input**

   * Audio chunks from toy microphone
   * Chunks sent as they become available

4. **Receive Audio Output**

   * Real-time audio stream from Little Krishna AI
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

### 3.2 Audio Response ← Server

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

### 3.3 Control Events ← Server

* Query responder speaking:

  ```json
  { "type": "QUERY_RESPONDER_SPEAKING" }
  ```
* Query responder finished:

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

## 4. Audio Specs

### Input (Toy Microphone → Server)

* PCM16LE
* 16 kHz
* Mono
* Base64 chunks

### Output (Server → Toy Speaker)

* PCM16LE
* 24 kHz
* Mono
* Base64 chunks

---

## 5. Implementation Checklist (ScholAR Toys)

* [ ] Connect WebSocket and wait for `READY`.
* [ ] Send `START_QUERY_SESSION`.
* [ ] Encode mic audio as **PCM16LE, 16 kHz**.
* [ ] Send chunks regularly (~20–40 ms).
* [ ] Handle `audio` response → decode base64 → play FIFO at **24 kHz**.
* [ ] Handle `QUERY_RESPONDER_SPEAKING` / `DONE` events.
* [ ] On user interrupt: send `USER_INTERRUPTED`.
* [ ] On session end: send `STOP_QUERY_SESSION` → expect `SESSION_ENDED`.
* [ ] Close WebSocket cleanly.

---
