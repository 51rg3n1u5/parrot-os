#!/usr/bin/env python3
"""
Touch input handler - reads multi-touch and sends via WebSocket.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

try:
    import evdev
    from evdev import InputDevice, ecodes
except ImportError:
    os.system("pip install evdev")
    import evdev
    from evdev import InputDevice, ecodes

clients = set()
touches = {}

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Client connected: {addr}")
    clients.add(writer)
    
    try:
        # WebSocket handshake
        data = await reader.read(1024)
        
        response = b"HTTP/1.1 101 Switching Protocols\r\n"
        response += b"Upgrade: websocket\r\n"
        response += b"Connection: Upgrade\r\n"
        response += b"\r\n"
        
        writer.write(response)
        await writer.drain()
        
        # Send welcome
        msg = json.dumps({"type": "connected"})
        await send_msg(writer, msg)
        
        print(f"Sent connected to {addr}")
        
        while True:
            data = await reader.read(2)
            if not data:
                break
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        clients.discard(writer)
        writer.close()

async def send_msg(writer, msg):
    try:
        data = msg.encode('utf-8')
        header = bytearray([0x81])
        header.append(len(data))
        writer.write(header + data)
        await writer.drain()
    except:
        pass

async def read_touch(device_path):
    """Read touch events from device"""
    dev = InputDevice(device_path)
    print(f"Reading from: {dev.name}")
    
    for event in dev.read_loop():
        if event.type == ecodes.EV_ABS:
            if event.code == ecodes.ABS_MT_TRACKING_ID:
                tid = event.value
                if tid == -1:
                    # Touch up
                    if touches:
                        key = list(touches.keys())[0]
                        del touches[key]
                        await broadcast({"type": "touch_end", "id": tid})
                else:
                    # Touch down
                    touches[tid] = {"x": 0, "y": 0}
                    await broadcast({"type": "touch_start", "id": tid})
                    
            elif event.code == ecodes.ABS_MT_POSITION_X:
                if touches:
                    key = list(touches.keys())[-1]
                    touches[key]["x"] = event.value
                    
            elif event.code == ecodes.ABS_MT_POSITION_Y:
                if touches:
                    key = list(touches.keys())[-1]
                    touches[key]["y"] = event.value
                    await broadcast({
                        "type": "touch_move",
                        "id": key,
                        "x": touches[key]["x"],
                        "y": touches[key]["y"]
                    })

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

async def main():
    # Find touch devices
    devices = []
    for path in Path('/dev/input').glob('event*'):
        try:
            dev = InputDevice(str(path))
            caps = dev.capabilities(verbose=False)
            if ecodes.EV_ABS in caps:
                abs_caps = caps.get(ecodes.EV_ABS, [])
                has_x = any(c[0] == ecodes.ABS_X for c in abs_caps)
                has_y = any(c[0] == ecodes.ABS_Y for c in abs_caps)
                if has_x and has_y:
                    print(f"Found: {dev.name}")
                    devices.append(path)
        except:
            pass
    
    if not devices:
        print("No touch devices!")
        return
    
    print(f"\n=== TOUCH READY ===")
    print(f"ws://localhost:8765")
    print(f"===================\n")
    
    # Start WS server
    server = await asyncio.start_server(handle_client, '0.0.0.0', 8765)
    
    # Start reading from first device
    asyncio.create_task(read_touch(devices[0]))
    
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
