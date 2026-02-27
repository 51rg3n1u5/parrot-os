#!/usr/bin/env python3
"""Touch input handler - broadcasts each touch with unique ID."""
import asyncio
import json
from pathlib import Path
from evdev import InputDevice, ecodes
import websockets

clients = set()
touches = {}  # tracking_id -> {x, y}

async def handle_client(websocket):
    addr = websocket.remote_address
    print(f"Client connected: {addr}")
    clients.add(websocket)
    
    try:
        await websocket.send(json.dumps({"type": "connected"}))
        
        async for msg in websocket:
            pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        clients.discard(websocket)

async def broadcast(data):
    if not clients:
        return
    msg = json.dumps(data)
    dead = set()
    for c in clients:
        try:
            await c.send(msg)
        except:
            dead.add(c)
    for c in dead:
        clients.discard(c)

async def read_device(path):
    dev = InputDevice(str(path))
    print(f"Reading from: {dev.name}")
    
    global touches
    
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_ABS:
            if event.code == ecodes.ABS_MT_TRACKING_ID:
                tid = event.value
                if tid == -1:
                    # Touch released - remove first touch
                    if touches:
                        removed_id = list(touches.keys())[0]
                        del touches[removed_id]
                        await broadcast({"type": "touch_end", "id": removed_id})
                else:
                    # New touch
                    touches[tid] = {"x": 0, "y": 0}
                    await broadcast({"type": "touch_start", "id": tid, "x": 0, "y": 0})
                    
            elif event.code == ecodes.ABS_MT_POSITION_X:
                if touches:
                    # Update most recent touch
                    tid = list(touches.keys())[-1]
                    touches[tid]["x"] = event.value
                    
            elif event.code == ecodes.ABS_MT_POSITION_Y:
                if touches:
                    tid = list(touches.keys())[-1]
                    touches[tid]["y"] = event.value
                    await broadcast({
                        "type": "touch_move",
                        "id": tid,
                        "x": touches[tid]["x"],
                        "y": touches[tid]["y"]
                    })

async def find_touch_device():
    for path in sorted(Path('/dev/input').glob('event*')):
        try:
            dev = InputDevice(str(path))
            caps = dev.capabilities(verbose=False)
            if ecodes.EV_ABS in caps:
                abs_caps = caps.get(ecodes.EV_ABS, [])
                has_x = any(c[0] == ecodes.ABS_X for c in abs_caps)
                has_y = any(c[0] == ecodes.ABS_Y for c in abs_caps)
                if has_x and has_y:
                    print(f"Found: {dev.name}")
                    return path
        except:
            pass
    return None

async def main():
    device = await find_touch_device()
    if not device:
        print("No touch device!")
        return
    
    print(f"\n=== TOUCH INPUT ===")
    print(f"ws://localhost:8765\n")
    
    async with websockets.serve(handle_client, '0.0.0.0', 8765):
        asyncio.create_task(read_device(device))
        await asyncio.Future()

asyncio.run(main())
