# pip install sounddevice websockets
import argparse, asyncio, queue, threading, time, sys
import sounddevice as sd
import websockets

async def run(url: str, device: int | None):
    # --- audio config ---
    sample_rate = 16000   # force 16kHz for speech
    channels = 1
    dtype = "int16"
    sample_width = 2      # bytes per sample (16-bit)

    # --- WebSocket connect ---
    async with websockets.connect(
        f"{url}&sr={sample_rate}&ch={channels}&sw={sample_width}"
    ) as ws:
        ack = await ws.recv()
        print("ACK:", ack)

        # --- audio capture ---
        q: "queue.Queue[bytes]" = queue.Queue(maxsize=32)
        stop = threading.Event()
        total_bytes = 0
        chunks = 0

        def callback(indata, frames, time_info, status):
            if status:
                print("status:", status, file=sys.stderr)
            try:
                q.put_nowait(indata.tobytes())
            except queue.Full:
                # drop if producer is faster than network
                pass

        blocksize = int(sample_rate * 0.02)  # 20 ms chunks

        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype=dtype,
            device=device,
            blocksize=blocksize,
            callback=callback,
        )

        async def sender():
            nonlocal total_bytes, chunks
            while not stop.is_set():
                try:
                    chunk = q.get(timeout=0.2)
                except queue.Empty:
                    await asyncio.sleep(0.05)
                    continue
                try:
                    await ws.send(chunk)
                except Exception as e:
                    print("send error:", e, file=sys.stderr)
                    stop.set()
                    break
                chunks += 1
                total_bytes += len(chunk)
                print(f"→ sent {len(chunk)} bytes")

        # --- run sender + stream ---
        sender_task = asyncio.create_task(sender())

        with stream:
            print("🎤 Recording... Ctrl+C to stop")
            try:
                while not stop.is_set():
                    await asyncio.sleep(0.2)
            except KeyboardInterrupt:
                pass

        stop.set()
        await sender_task

        secs = total_bytes / (sample_width * channels * sample_rate)
        print(f"[closed] sent_chunks={chunks}, total_bytes={total_bytes}, ~duration={secs:.2f}s")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--url",
        default="ws://localhost:8000/ws/audio?filename=cli_test.wav",
        help="server ws endpoint (without sr/ch/sw, they’re added automatically)",
    )
    ap.add_argument(
        "--device",
        type=int,
        default=None,
        help="Input device index (use sounddevice.query_devices() to list)",
    )
    args = ap.parse_args()
    asyncio.run(run(args.url, args.device))
