# app/websocket/routes.py (inside register_ws_routes)
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosedOK
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
                    try:
                        while ws.client_state == WebSocketState.CONNECTED:
                            try:
                                msg = await ws.receive()
                                
                                if msg["type"] == "websocket.disconnect":
                                    logger.info("Disconnect message received")
                                    break
                                    
                                if msg["type"] == "websocket.receive":
                                    if (b := msg.get("bytes")) is not None:
                                        await adapter.send_audio(b)
                                        continue
                                    if (t := msg.get("text")):
                                        try:
                                            obj = json.loads(t)
                                            if obj.get("type") == "text":
                                                await adapter.send_text(obj.get("data", ""))
                                        except json.JSONDecodeError:
                                            logger.warning("Ignoring non-JSON control message")
                                        except Exception as e:
                                            logger.error(f"Error processing text message: {e}")
                                            
                            except WebSocketDisconnect:
                                logger.info("WebSocket disconnect in recv_loop")
                                break
                            except Exception as e:
                                logger.error(f"Error in recv_loop: {e}")
                                break
                                
                    except Exception as e:
                        logger.error(f"Fatal error in recv_loop: {e}")

                async def send_loop():
                    try:
                        async for ev in adapter.events():
                            if ws.client_state != WebSocketState.CONNECTED:
                                logger.info("WebSocket not connected, stopping send loop")
                                break
                            try:
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
                            except WebSocketDisconnect:
                                logger.info("WebSocket disconnected during send")
                                break
                            except Exception as e:
                                logger.error(f"Error sending event: {e}")
                                break
                    except Exception as e:
                        logger.info(f"Adapter event stream ended: {e}")

                # Use asyncio.wait instead of TaskGroup for better exception handling
                recv_task = asyncio.create_task(recv_loop())
                send_task = asyncio.create_task(send_loop())
                
                try:
                    # Wait for either task to complete or raise an exception
                    done, pending = await asyncio.wait(
                        [recv_task, send_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel remaining tasks
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                    
                    # Check if any task raised an exception (excluding normal disconnections)
                    for task in done:
                        try:
                            task.result()
                        except (WebSocketDisconnect, ConnectionClosedOK):
                            logger.info("WebSocket connection closed normally")
                        except Exception as e:
                            logger.error(f"Task completed with error: {e}")
                            
                except Exception as e:
                    logger.error(f"Error in task management: {e}")
                    # Cancel both tasks
                    recv_task.cancel()
                    send_task.cancel()

        except WebSocketDisconnect:
            logger.info(f"WS disconnected: {client_id}")
        except Exception as e:
            logger.exception(f"WS error: {e}")
        finally:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.close()
            except Exception:
                pass
            logger.info(f"WebSocket connection cleanup complete: {client_id}")