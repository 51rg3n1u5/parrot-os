#!/usr/bin/env python3
"""Touch input handler - using websockets library for proper WS handling."""
import asyncio
import json
from pathlib import Path
from evdev import InputDevice, ecodes
import websockets

clients = set()
current_touches = {}

async def handle_client(websocket):
    """Handle a WebSocket client connection."""
    addr = websocket.remote_address
    print(f"Client connected: {addr}")
    clients.add(websocket)
    
    try:
        # Send welcome
        await websocket.send(json.dumps({"type": "connected"}))
        print(f"Sent connected to {addr}")
        
        # Keep alive - just listen
        async for msg in websocket:
            print(f"Received: {msg}")
            
    except websockets.exceptions.ConnectionClosed:
        print(f"Client {addr} disconnected")
    except Exception as e:
        print(f"Error with {addr}: {e}")
    finally:
        clients.discard(websocket)

async def broadcast(data):
    """Broadcast to all clients."""
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
    """Read touch events from device."""
    dev = InputDevice(str(path))
    print(f"Reading from: {dev.name}")
    
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_ABS:
            if event.code == ecodes.ABS_MT_TRACKING_ID:
                tid = event.value
                if tid == -1:
                    if current_touches:
                        current_touches.pop(list(current_touches.keys())[0], None)
                        await broadcast({"type": "touch_end"})
                else:
                    current_touches[tid] = {"x": 0, "y": 0}
                    await broadcast({"type": "touch_start", "id": tid})
                    
            elif event.code == ecodes.ABS_MT_POSITION_X:
                if current_touches:
                    key = list(current_touches.keys())[-1]
                    current_touches[key]["x"] = event.value
                    
            elif event.code == ecodes.ABS_MT_POSITION_Y:
                if current_touches:
                    key = list(current_touches.keys())[-1]
                    current_touches[key]["y"] = event.value
                    await broadcast({
                        "type": "touch_move",
                        "x": current_touches[key]["x"],
                        "y": current_touches[key]["y"]
                    })

async def find_touch_device():
    """Find the first touch device."""
    for path in sorted(Path('/dev/input').glob('event*')):
        try:
            dev = InputDevice(str(path))
            caps = dev.capabilities(verbose=False)
            if ecodes.EV_ABS in caps:
                abs_caps = caps.get(ecodes.EV_ABS, [])
                has_x = any(c[0] == ecodes.ABS_X for c in abs_caps)
                has_y = any(c[0] == ecodes.ABS_Y for c in abs_caps)
                if has_x and has_y:
                    print(f"Found: {dev.name} ({path})")
                    return path
        except:
            pass
    return None

async def main():
    device = await find_touch_device()
    
    if not device:
        print("ERROR: No touch device!")
        return
    
    print(f"\n=== TOUCH INPUT ===")
    print(f"ws://localhost:8765")
    print(f"==================\n")
    
    # Start WebSocket server using websockets library
    async with websockets.serve(handle_client, '0.0.0.0', 8765):
        print("Server started, waiting for clients...")
        
        # Start reading device
        asyncio.create_task(read_device(device))
        
        # Run forever
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(main())
