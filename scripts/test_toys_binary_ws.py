import asyncio
import websockets
import json
import sys

# Configuration
URI = "ws://localhost:8000/ws/toys/queries"
DEVICE_ID = "test-device-001"
TOKEN = "test-token"  # You might need a valid token if auth is enabled

async def test_binary_protocol():
    print(f"Connecting to {URI}...")
    try:
        async with websockets.connect(
            f"{URI}?device_id={DEVICE_ID}", 
            extra_headers={"Authorization": f"Bearer {TOKEN}"}
        ) as websocket:
            print("Connected!")

            # 1. Send Start Session Message (JSON)
            start_msg = {
                "type": "START_QUERY_SESSION",
                "device_id": DEVICE_ID
            }
            await websocket.send(json.dumps(start_msg))
            print(f"Sent: {start_msg}")

            # 2. Listen for messages
            print("Listening for messages...")
            audio_chunks_received = 0
            binary_frames_received = 0
            
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    
                    if isinstance(message, bytes):
                        # BINARY FRAME - This is what we want!
                        binary_frames_received += 1
                        audio_chunks_received += 1
                        print(f"[PASS] Received Binary Frame: {len(message)} bytes")
                        
                        # Verify chunk size is within MTU limits (approx)
                        if len(message) > 1500:
                            print(f"[WARN] Chunk size {len(message)} exceeds typical MTU (1500)")
                        
                    elif isinstance(message, str):
                        # TEXT FRAME - Control message
                        data = json.loads(message)
                        print(f"Received Control Message: {data.get('type')}")
                        
                        if data.get("type") == "QUERY_RESPONDER_DONE":
                            print("Stream finished.")
                            break
                            
            except asyncio.TimeoutError:
                print("Timeout waiting for response.")
            
            print("-" * 30)
            print(f"Total Audio Chunks: {audio_chunks_received}")
            print(f"Binary Frames: {binary_frames_received}")
            
            if binary_frames_received > 0:
                print("✅ SUCCESS: Protocol is using Binary Frames!")
            else:
                print("❌ FAILURE: No binary frames received.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Install websockets if missing: pip install websockets
    asyncio.run(test_binary_protocol())
