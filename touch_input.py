#!/usr/bin/env python3
"""Touch input handler - using evdev async."""
import asyncio
import json
from pathlib import Path
from evdev import InputDevice, ecodes

clients = set()

async def handle_client(reader, writer):
    print(f"Client connected")
    clients.add(writer)
    
    try:
        data = await reader.read(1024)
        
        response = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n"
        writer.write(response)
        await writer.drain()
        
        await send_msg(writer, json.dumps({"type": "connected"}))
        
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
        writer.write(bytes([0x81, len(data)]) + data)
        await writer.drain()
    except:
        pass

async def broadcast(data):
    msg = json.dumps(data)
    for c in list(clients):
        try:
            await send_msg(c, msg)
        except:
            clients.discard(c)

async def read_device(path):
    dev = InputDevice(str(path))
    print(f"Reading from: {dev.name}")
    
    # Use async generator
    async for event in dev.async_read_loop():
        if event.type == ecodes.EV_ABS:
            if event.code == ecodes.ABS_MT_POSITION_X:
                await broadcast({"type": "x", "value": event.value})
            elif event.code == ecodes.ABS_MT_POSITION_Y:
                await broadcast({"type": "y", "value": event.value})

async def main():
    devices = [p for p in Path('/dev/input').glob('event*') 
               if 'touch' in p.stem.lower() or 'event' in str(p)]
    
    print("=== TOUCH READY ===")
    print("ws://localhost:8765")
    
    server = await asyncio.start_server(handle_client, '0.0.0.0', 8765)
    
    if devices:
        asyncio.create_task(read_device(devices[0]))
    
    async with server:
        await server.serve_forever()

asyncio.run(main())
