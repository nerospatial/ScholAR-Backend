# app/websocket/routes.py (inside register_ws_routes)
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.core.log import logger
from app.schemas.messages import (
    READY, TYPE_TEXT, TYPE_TURN_COMPLETE, TYPE_SESSION_ID, TYPE_INTERRUPTED
)
from app.llm.base import AudioOut, TextOut, TurnComplete, SessionId, GoAway, Interrupted
from app.llm.providers import get_adapter_cls
from app.core.settings import Settings

def register_ws_routes(app: FastAPI) -> None:
    AdapterCls = get_adapter_cls(Settings.llm_provider)

    @app.websocket("/ws/audio")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        await ws.send_json(READY)
        client_id = id(ws)
        logger.info(f"WS connected: {client_id} (provider={Settings.llm_provider})")

        try:
            async with AdapterCls() as adapter:

                async def recv_loop():
                    while True:
                        msg = await ws.receive()
                        if (b := msg.get("bytes")) is not None:
                            await adapter.send_audio(b)
                            continue
                        if (t := msg.get("text")):
                            try:
                                obj = json.loads(t)
                                if obj.get("type") == "text":
                                    await adapter.send_text(obj.get("data", ""))
                            except Exception:
                                logger.warning("Ignoring non-JSON control message")

                async def send_loop():
                    try:
                        async for ev in adapter.events():
                            if isinstance(ev, AudioOut):
                                await ws.send_bytes(ev.pcm)
                            elif isinstance(ev, TextOut):
                                await ws.send_json({"type": TYPE_TEXT, "data": ev.text})
                            elif isinstance(ev, TurnComplete):
                                await ws.send_json({"type": TYPE_TURN_COMPLETE})
                            elif isinstance(ev, SessionId):
                                await ws.send_json({"type": TYPE_SESSION_ID, "data": ev.id})
                            elif isinstance(ev, Interrupted):
                                await ws.send_json({"type": TYPE_INTERRUPTED, "data": "Response interrupted by user input"})
                            elif isinstance(ev, GoAway):
                                logger.info(f"Session will terminate in {ev.time_left:.2f}s")
                    except Exception as e:
                        # Normal end or adapter already logged it — just exit the task
                        logger.info(f"Adapter event stream ended: {e}")

                async with asyncio.TaskGroup() as tg:
                    tg.create_task(recv_loop())
                    tg.create_task(send_loop())

        except WebSocketDisconnect:
            logger.info(f"WS disconnected: {client_id}")
        except Exception as e:
            logger.exception(f"WS error: {e}")
            try:
                await ws.close()
            except Exception:
                pass
