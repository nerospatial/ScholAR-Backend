# app/websocket/audio_ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.audio_ws_service import AudioWSService
from app.websocket.connection import manager
from app.schemas.ws.audio import WSOut, AckPayload, ErrorPayload

router = APIRouter()

@router.websocket("/ws/audio")
async def audio_ws(
    ws: WebSocket,
    sr: int = Query(16000, ge=8000, le=96000),
    ch: int = Query(1, ge=1, le=2),
    sw: int = Query(2, ge=1, le=4),
    filename: str | None = Query(default=None),
):
    await manager.accept(ws)
    sess = AudioWSService.start(
        ws, sample_rate=sr, channels=ch, sample_width=sw, filename=filename
    )
    await ws.send_text(
        WSOut(type="ack", data=AckPayload(session_id=sess.id, path=str(sess.path))).model_dump_json()
    )

    # --- metrics + safety ---
    frame_size = ch * sw                      # bytes per audio frame (sample across all channels)
    total_bytes = 0
    chunks = 0
    residual = b""                            # carry unaligned tail between frames

    try:
        while True:
            data = await ws.receive_bytes()   # binary-only hot path
            chunks += 1
            total_bytes += len(data)
            print(f"← recv {len(data)} bytes")   # per-packet log

            # ensure we only write whole frames (avoid partial samples)
            buf = residual + data
            aligned = (len(buf) // frame_size) * frame_size
            if aligned:
                AudioWSService.write(ws, buf[:aligned])
            residual = buf[aligned:]          # keep leftover for next loop

    except WebSocketDisconnect:
        if residual:
            # if the client closed mid-frame, drop tail (or pad if you prefer)
            print(f"[warn] dropping {len(residual)} trailing bytes (not aligned to frame_size={frame_size})")
        manager.disconnect(ws)
        # duration = total_frames / sample_rate
        approx_seconds = (total_bytes // frame_size) / sr if sr else 0.0
        print(
            f"[closed] chunks={chunks}, total_bytes={total_bytes}, "
            f"~duration={approx_seconds:.2f}s, file={sess.path}"
        )

    except Exception as e:
        try:
            await ws.send_text(
                WSOut(type="error", data=ErrorPayload(code="internal_error", message=str(e))).model_dump_json()
            )
        except Exception:
            pass
        manager.disconnect(ws)
        raise
