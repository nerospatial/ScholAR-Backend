# ScholAR WebSocket Test Client

A comprehensive Python client for testing the ScholAR backend WebSocket implementation.

## Features

- **Text Chat Mode**: Interactive text conversation with the AI
- **Audio Streaming Mode**: Real-time microphone input and audio playback
- **Video Streaming Mode**: Camera capture and streaming to the backend
- **Session Management**: Proper session start/stop handling
- **Error Handling**: Robust error handling and connection management

## Requirements

Install the required dependencies:

```bash
pip install websockets pyaudio opencv-python pillow
```

### Platform-specific PyAudio installation:

**Ubuntu/Debian:**

```bash
sudo apt-get install portaudio19-dev
pip install pyaudio
```

**macOS:**

```bash
brew install portaudio
pip install pyaudio
```

**Windows:**

```bash
pip install pyaudio
```

## Usage

### Text Mode (Default)

```bash
python ws_test_client.py --mode text
```

Interactive text chat:

- Type `start` to begin a session
- Type your messages to chat with the AI
- Type `stop` to end the session
- Type `quit` to exit

### Audio Mode

```bash
python ws_test_client.py --mode audio
```

Real-time audio conversation:

- Press Enter to start the session
- Speak into your microphone
- Listen to AI audio responses
- Press Enter again to stop

### Video Mode

```bash
python ws_test_client.py --mode video
```

Video streaming with your camera:

- Press Enter to start the session
- Camera frames are sent every second
- Press Enter again to stop

### Custom Server URL

```bash
python ws_test_client.py --url ws://your-server:port/ws/queries
```

## Configuration

The client automatically matches your backend settings:

```python
WEBSOCKET_URL = "ws://localhost:8000/ws/queries"
FORMAT = pyaudio.paInt16  # 16-bit audio
CHANNELS = 1              # Mono
SEND_SAMPLE_RATE = 16000  # Input sample rate
RECEIVE_SAMPLE_RATE = 24000  # Output sample rate
CHUNK_SIZE = 1024         # Audio chunk size
```

## Message Protocol

### Outgoing Messages:

```json
// Session control
{"type": "START_QUERY_SESSION"}
{"type": "STOP_QUERY_SESSION"}
{"type": "USER_INTERRUPTED"}

// Data messages
{"type": "text", "data": "Hello"}
{"type": "audio", "data": "base64_audio", "sample_rate": 16000}
{"type": "video", "data": "base64_image", "mime_type": "image/jpeg"}
```

### Incoming Messages:

```json
// Status messages
"READY"
"QUERY_RESPONDER_SPEAKING"
"QUERY_RESPONDER_DONE"
"SESSION_ENDED"

// Responses
{"type": "text_response", "data": "AI response"}
{"type": "audio_response", "data": "base64_audio_chunk"}
{"type": "ERROR", "message": "Error description"}
```

## Example Output

```
🚀 Starting ScholAR Test Client in text mode
🔗 Connecting to: ws://localhost:8000/ws/queries
Connected to ws://localhost:8000/ws/queries
Server says: READY

💬 Text chat mode. Type 'quit' to exit, 'start' to begin session.

You: start
📡 Status: START_QUERY_SESSION

You: Hello, can you help me with math?
🤖 AI: Hello! I'd be happy to help you with math. What specific math topic or problem would you like assistance with?

You: stop
📡 Status: SESSION_ENDED

You: quit
Exiting...
Disconnected and cleaned up resources
```

## Troubleshooting

### Audio Issues

- Ensure your microphone is working and not used by other applications
- Check audio permissions on your system
- Try different audio devices if default doesn't work

### Video Issues

- Make sure your camera is connected and working
- Check camera permissions
- Only one application can use the camera at a time

### Connection Issues

- Verify the backend server is running on the correct port
- Check firewall settings
- Ensure the WebSocket URL is correct

## Development

The client is designed to be easily extensible:

- Add new message types in `process_response()`
- Modify audio/video settings in the configuration section
- Add new modes by extending the `ScholARTestClient` class
- Customize the UI by modifying the print statements and input handling

## Architecture

```
ScholARTestClient
├── Connection Management (connect/disconnect)
├── Session Management (start/stop session)
├── Media Capture (audio/video streaming)
├── Message Handling (send/receive)
├── Response Processing (text/audio playback)
└── Mode Controllers (text/audio/video)
```

This client provides a complete testing environment for your ScholAR WebSocket backend!
