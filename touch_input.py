#!/usr/bin/env python3
"""Touch input handler - reads multi-touch and broadcasts via WebSocket."""
import asyncio
import json
from pathlib import Path
from evdev import InputDevice, ecodes

clients = set()
current_touches = {}

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Client connected: {addr}")
    clients.add(writer)
    
    try:
        # Read WebSocket upgrade request
        data = await reader.read(1024)
        
        # Send 101 Switching Protocols
        response = b"HTTP/1.1 101 Switching Protocols\r\n"
        response += b"Upgrade: websocket\r\n"
        response += b"Connection: Upgrade\r\n"
        response += b"\r\n"
        
        writer.write(response)
        await writer.drain()
        
        # Send welcome message
        await send_msg(writer, json.dumps({"type": "connected"}))
        print(f"Sent connected to {addr}")
        
        # Keep connection alive
        while True:
            data = await reader.read(2)
            if not data:
                break
                
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        clients.discard(writer)
        writer.close()

async def send_msg(writer, msg):
    try:
        data = msg.encode('utf-8')
        header = bytes([0x81, len(data)])
        writer.write(header + data)
        await writer.drain()
    except Exception as e:
        print(f"Send error: {e}")

async def broadcast(data):
    msg = json.dumps(data)
    dead = set()
    for c in clients:
        try:
            await send_msg(c, msg)
        except:
            dead.add(c)
    for c in dead:
        clients.discard(c)

async def read_device(path):
    """Read touch events from device."""
    dev = InputDevice(str(path))
    print(f"Reading from: {dev.name}")
    print("Waiting for touch events...")
    
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_ABS:
            if event.code == ecodes.ABS_MT_TRACKING_ID:
                tid = event.value
                if tid == -1:
                    # Touch released
                    if current_touches:
                        old = current_touches.pop(list(current_touches.keys())[0], None)
                        if old:
                            await broadcast({"type": "touch_end", "id": tid})
                else:
                    # New touch
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
                        "id": key,
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
                    print(f"Found touch device: {dev.name} ({path})")
                    return path
        except:
            pass
    return None

async def main():
    device = await find_touch_device()
    
    if not device:
        print("ERROR: No touch device found!")
        return
    
    print(f"\n=== TOUCH INPUT READY ===")
    print(f"WebSocket: ws://localhost:8765")
    print(f"Device: {device}")
    print(f"========================\n")
    
    # Start WebSocket server
    server = await asyncio.start_server(handle_client, '0.0.0.0', 8765)
    
    # Start reading from device
    asyncio.create_task(read_device(device))
    
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
