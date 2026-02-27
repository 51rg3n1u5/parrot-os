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

# Global state
active_touches = {}  # tracking_id -> {x, y}
clients = set()

def find_touch_devices():
    """Find all touch input devices"""
    devices = []
    for path in sorted(Path('/dev/input').glob('event*')):
        try:
            dev = InputDevice(str(path))
            caps = dev.capabilities(verbose=False)
            
            if ecodes.EV_ABS in caps:
                abs_caps = caps.get(ecodes.EV_ABS, [])
                has_x = any(c[0] == ecodes.ABS_X for c in abs_caps)
                has_y = any(c[0] == ecodes.ABS_Y for c in abs_caps)
                has_mt = any(c[0] == ecodes.ABS_MT_POSITION_X for c in abs_caps)
                
                if has_x and has_y:
                    print(f"Found touch: {dev.name} ({path})")
                    devices.append(path)
        except Exception as e:
            print(f"Error: {e}")
            pass
    
    return devices

async def handle_device(device_path, queue):
    """Read events from device and put in queue"""
    try:
        dev = InputDevice(str(device_path))
        print(f"Reading from: {dev.name}")
        
        for event in dev.read_loop():
            await queue.put(event)
            
    except Exception as e:
        print(f"Device error: {e}")

async def process_events(queue):
    """Process events from all devices"""
    global active_touches
    
    while True:
        event = await queue.get()
        
        if event.type == ecodes.EV_ABS:
            if event.code == ecodes.ABS_MT_TRACKING_ID:
                tid = event.value
                if tid == -1:
                    # Touch lifted - remove any touch
                    if active_touches:
                        removed = active_touches.pop(list(active_touches.keys())[0], None)
                        if removed:
                            await broadcast({'type': 'touch_end', 'id': tid})
                else:
                    # New touch
                    active_touches[tid] = {'x': 0, 'y': 0}
                    await broadcast({'type': 'touch_start', 'id': tid})
            
            elif event.code == ecodes.ABS_MT_POSITION_X:
                tid = event.value if False else (list(active_touches.keys())[-1] if active_touches else 0)
                if tid in active_touches:
                    active_touches[tid]['x'] = event.value
                    await broadcast({
                        'type': 'touch_move',
                        'id': tid,
                        'x': active_touches[tid]['x'],
                        'y': active_touches[tid].get('y', 0)
                    })
            
            elif event.code == ecodes.ABS_MT_POSITION_Y:
                tid = event.value if False else (list(active_touches.keys())[-1] if active_touches else 0)
                if tid in active_touches:
                    active_touches[tid]['y'] = event.value
                    await broadcast({
                        'type': 'touch_move',
                        'id': tid,
                        'x': active_touches[tid].get('x', 0),
                        'y': active_touches[tid]['y']
                    })

async def broadcast(data):
    """Broadcast to all WebSocket clients"""
    if clients:
        msg = json.dumps(data)
        dead_clients = set()
        for client in clients:
            try:
                # Simple text frame
                msg_bytes = msg.encode('utf-8')
                frame = bytearray([0x81])  # TEXT frame
                if len(msg_bytes) < 126:
                    frame.append(len(msg_bytes))
                elif len(msg_bytes) < 65536:
                    frame.extend([126, (len(msg_bytes) >> 8) & 0xFF, len(msg_bytes) & 0xFF])
                else:
                    frame.extend([127, 0, 0, 0, 0, (len(msg_bytes) >> 24) & 0xFF, (len(msg_bytes) >> 16) & 0xFF, (len(msg_bytes) >> 8) & 0xFF, len(msg_bytes) & 0xFF])
                frame.extend(msg_bytes)
                client.write(frame)
                await client.drain()
            except Exception as e:
                print(f"Broadcast error: {e}")
                dead_clients.add(client)
        
        for c in dead_clients:
            clients.discard(c)

async def handle_client(reader, writer):
    """Handle WebSocket client"""
    try:
        # Read HTTP request
        data = await reader.read(1024)
        request = data.decode('utf-8', errors='ignore')
        
        # Simple WebSocket handshake - respond with 101
        response = b'''HTTP/1.1 101 Switching Protocols\r
Upgrade: websocket\r
Connection: Upgrade\r
Sec-WebSocket-Accept: Sockets\r
\r
'''
        writer.write(response)
        await writer.drain()
        
        clients.add(writer)
        print(f"Client connected! Total: {len(clients)}")
        
        # Keep alive - read ping frames
        while True:
            data = await reader.read(2)
            if not data:
                break
            # Pong
            if data[0] == 0x89:
                writer.write(bytes([0x8A, 0x00]))
                await writer.drain()
                
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        clients.discard(writer)
        try:
            writer.close()
        except:
            pass

async def main():
    devices = find_touch_devices()
    
    if not devices:
        print("ERROR: No touch devices found!")
        sys.exit(1)
    
    print(f"\nStarting touch handler...")
    print(f"WebSocket: ws://localhost:8765")
    print("Press Ctrl+C to stop\n")
    
    # Start WebSocket server
    server = await asyncio.start_server(
        handle_client,
        '0.0.0.0',
        8765
    )
    
    queue = asyncio.Queue()
    
    # Start device readers
    tasks = []
    for device in devices:
        tasks.append(asyncio.create_task(handle_device(device, queue)))
    
    # Start event processor
    tasks.append(asyncio.create_task(process_events(queue)))
    
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
