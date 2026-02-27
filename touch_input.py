#!/usr/bin/env python3
"""Touch input handler - properly tracks multi-touch using slots."""
import asyncio
import json
from pathlib import Path
from evdev import InputDevice, ecodes
import websockets

clients = set()
touches = {}  # slot -> {tracking_id, x, y}
current_slot = 0

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
    global current_slot
    dev = InputDevice(str(path))
    print(f"Reading from: {dev.name}")
    
    # Track tracking_id -> slot mapping
    tid_to_slot = {}
    
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_ABS:
            # Handle slot changes
            if event.code == ecodes.ABS_MT_SLOT:
                current_slot = event.value
                
            elif event.code == ecodes.ABS_MT_TRACKING_ID:
                tid = event.value
                if tid == -1:
                    # Touch released - find and remove this slot
                    slot_to_remove = None
                    for slot, info in tid_to_slot.items():
                        if info.get('tid') == current_slot:
                            slot_to_remove = slot
                            break
                    if slot_to_remove:
                        del touches[slot_to_remove]
                        del tid_to_slot[slot_to_remove]
                        await broadcast({"type": "touch_end", "slot": slot_to_remove})
                else:
                    # New touch
                    tid_to_slot[current_slot] = {"tid": tid}
                    touches[current_slot] = {"tid": tid, "x": 0, "y": 0}
                    await broadcast({"type": "touch_start", "slot": current_slot, "x": 0, "y": 0})
                    
            elif event.code == ecodes.ABS_MT_POSITION_X:
                if current_slot in touches:
                    touches[current_slot]["x"] = event.value
                    
            elif event.code == ecodes.ABS_MT_POSITION_Y:
                if current_slot in touches:
                    touches[current_slot]["y"] = event.value
                    await broadcast({
                        "type": "touch_move",
                        "slot": current_slot,
                        "x": touches[current_slot]["x"],
                        "y": touches[current_slot]["y"]
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
