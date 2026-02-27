#!/usr/bin/env python3
"""
Touch input handler - reads multi-touch directly from /dev/input
and broadcasts to web clients via WebSocket.
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
    print("Installing evdev...")
    os.system("pip install evdev")
    import evdev
    from evdev import InputDevice, ecodes

async def echo(reader, writer):
    """Simple echo server for testing WebSocket"""
    addr = writer.get_extra_info('peername')
    print(f"Client connected from {addr}")
    
    try:
        # Read request
        data = await reader.read(1024)
        print(f"Received: {data[:100]}")
        
        # Send WebSocket handshake
        response = b"HTTP/1.1 101 Switching Protocols\r\n"
        response += b"Upgrade: websocket\r\n"
        response += b"Connection: Upgrade\r\n"
        response += b"\r\n"
        
        writer.write(response)
        await writer.drain()
        print("Sent 101 response")
        
        # Keep alive
        while True:
            data = await reader.read(256)
            if not data:
                break
            print(f"Received data: {data}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Client disconnected")
        writer.close()

async def main():
    # Find devices
    devices = []
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
                    devices.append(path)
        except:
            pass
    
    if not devices:
        print("No touch devices found!")
        sys.exit(1)
    
    print(f"\n=== TOUCH INPUT READY ===")
    print(f"ws://localhost:8765")
    print(f"Devices: {devices}")
    print(f"========================\n")
    
    server = await asyncio.start_server(echo, '0.0.0.0', 8765)
    
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
