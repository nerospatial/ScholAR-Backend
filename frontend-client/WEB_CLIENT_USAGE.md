# Web Test Client Usage Instructions

## Fixed Issues

### getUserMedia Error Resolution

The web test client now includes comprehensive error handling for media device access:

1. **Browser Compatibility Check**: Automatically checks for WebSocket, MediaDevices API, and Web Audio API support
2. **Security Context Detection**: Verifies HTTPS or localhost requirement for camera/microphone access
3. **Detailed Error Messages**: Provides specific guidance for different error scenarios:
   - Permission denied
   - Device not found
   - Browser not supported
   - Device in use by another application
   - HTTPS requirement

## Running the Web Test Client

### Option 1: Using the HTTP Server (Recommended)

```bash
cd frontend-client
python3 serve_web_client.py
```

Then open: http://localhost:8081/web_test_client.html

### Option 2: Direct File Access

Open `web_test_client.html` directly in a modern browser, but note:

- Camera/microphone access requires HTTPS or localhost
- File:// protocol may not work for media devices

## Browser Requirements

### Supported Browsers

- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+

### Required Features

- WebSocket API
- MediaDevices API (getUserMedia)
- Web Audio API
- Secure context (HTTPS/localhost)

## Usage Flow

1. **Open the web client** at http://localhost:8081/web_test_client.html
2. **Check compatibility** - The page will automatically run a browser compatibility check
3. **Connect to WebSocket** - Click "Connect to Server" (ensure backend is running on localhost:8000)
4. **Grant permissions** - Click "Start Session" and allow camera/microphone access
5. **Test streaming** - Speak or move in front of the camera to test audio/video streaming
6. **Monitor status** - Watch the connection status indicators and log messages

## Troubleshooting

### Common Issues

#### "getUserMedia not supported"

- **Cause**: Not using HTTPS or localhost
- **Solution**: Use the provided HTTP server or deploy over HTTPS

#### "Camera/microphone access denied"

- **Cause**: User denied permissions
- **Solution**: Click the camera icon in browser address bar to allow permissions

#### "No camera or microphone found"

- **Cause**: No media devices connected
- **Solution**: Connect a webcam and microphone, then refresh

#### "Device already in use"

- **Cause**: Another application is using the camera/microphone
- **Solution**: Close other applications using media devices

#### WebSocket connection fails

- **Cause**: Backend server not running
- **Solution**: Start the FastAPI backend server on localhost:8000

## Testing with Backend

Ensure your FastAPI backend is running:

```bash
cd ScholAR-Backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The web client will connect to: `ws://localhost:8000/ws/queries`

## Features Tested

- ✅ Real-time audio streaming (PCM 16-bit, 16kHz)
- ✅ Real-time video streaming (640x480, 30fps)
- ✅ WebSocket message handling
- ✅ Session management
- ✅ Audio visualization
- ✅ Error handling and recovery
- ✅ Cross-browser compatibility checks
