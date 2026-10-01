"""WebSocket endpoint for real-time event broadcasting to connected frontend clients."""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from context_cockpit.services.event_bus import ContextChangeEvent, global_event_bus

ws_router = APIRouter(tags=["realtime"])


@ws_router.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket) -> None:
    """Streams real-time file update and mutation events to the browser client."""
    await websocket.accept()
    queue = await global_event_bus.subscribe()

    try:
        while True:
            # Wait for event from bus or client ping
            event_task = asyncio.create_task(queue.get())
            recv_task = asyncio.create_task(websocket.receive_text())

            done, pending = await asyncio.wait(
                [event_task, recv_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            if event_task in done:
                event: ContextChangeEvent = event_task.result()
                await websocket.send_json(
                    {
                        "type": "context_updated",
                        "filename": event.filename,
                        "event_type": event.event_type,
                        "timestamp": event.timestamp,
                        "metadata": event.metadata,
                    }
                )

            if recv_task in done:
                data = recv_task.result()
                if data == "ping":
                    await websocket.send_text("pong")
    except (WebSocketDisconnect, ConnectionResetError):
        pass
    finally:
        await global_event_bus.unsubscribe(queue)
