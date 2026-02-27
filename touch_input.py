#!/usr/bin/env python3
"""
Touch input handler - reads multi-touch directly from /dev/input
and broadcasts to web clients via WebSocket.
"""
import asyncio
import json
import os
import signal
import sys
from pathlib import Path

# Try to import evdev, install if missing
try:
    import evdev
    from evdev import InputDevice, AbsInfo, ecodes
except ImportError:
    print("Installing evdev...")
    os.system("pip install evdev")
    import evdev
    from evdev import InputDevice, AbsInfo, ecodes

class TouchHandler:
    def __init__(self):
        self.devices = {}
        self.touches = {}  # tracking_id -> {x, y}
        self.clients = set()
        
    def find_touch_devices(self):
        """Find all touch input devices"""
        touch_devices = []
        for path in Path('/dev/input').glob('event*'):
            try:
                dev = InputDevice(path)
                capabilities = dev.capabilities(verbose=False)
                
                # Check if it has absolute position (touch)
                if ecodes.EV_ABS in capabilities:
                    abs_caps = capabilities.get(ecodes.EV_ABS, [])
                    has_x = any(cap[0] == ecodes.ABS_X for cap in abs_caps)
                    has_y = any(cap[0] == ecodes.ABS_Y for cap in abs_caps)
                    
                    if has_x and has_y:
                        print(f"Found touch device: {dev.name} ({path})")
                        touch_devices.append(path)
            except Exception as e:
                pass
        
        if not touch_devices:
            print("No touch devices found! Trying event0...")
            touch_devices = [Path('/dev/input/event0')]
        
        return touch_devices
    
    async def handle_device(self, device_path):
        """Read events from one device"""
        try:
            dev = InputDevice(str(device_path))
            print(f"Reading from: {dev.name}")
            
            async for event in dev.async_read_loop():
                if event.type == ecodes.EV_ABS:
                    tracking_id = None
                    
                    # Get tracking ID for this touch
                    mt_slot = dev.properties.get('ABS_MT_TRACKING_ID')
                    
                    if event.code == ecodes.ABS_MT_TRACKING_ID:
                        tracking_id = event.value
                        if tracking_id == -1:  # Touch lifted
                            # Find and remove this touch
                            for tid, t in list(self.touches.items()):
                                if t.get('slot') == event.value:
                                    del self.touches[tid]
                                    await self.broadcast({'type': 'touch_end', 'id': tid})
                                    break
                        else:
                            # New touch
                            self.touches[tracking_id] = {'slot': tracking_id}
                            await self.broadcast({'type': 'touch_start', 'id': tracking_id})
                    
                    elif event.code == ecodes.ABS_MT_POSITION_X:
                        if tracking_id is None:
                            tracking_id = len(self.touches)
                        if tracking_id not in self.touches:
                            self.touches[tracking_id] = {'slot': tracking_id}
                        self.touches[tracking_id]['x'] = event.value
                        await self.broadcast({
                            'type': 'touch_move',
                            'id': tracking_id,
                            'x': event.value,
                            'y': self.touches[tracking_id].get('y', 0)
                        })
                    
                    elif event.code == ecodes.ABS_MT_POSITION_Y:
                        if tracking_id is None:
                            tracking_id = len(self.touches)
                        if tracking_id not in self.touches:
                            self.touches[tracking_id] = {'slot': tracking_id}
                        self.touches[tracking_id]['y'] = event.value
                        await self.broadcast({
                            'type': 'touch_move',
                            'id': tracking_id,
                            'x': self.touches[tracking_id].get('x', 0),
                            'y': event.value
                        })
                        
                elif event.type == ecodes.EV_SYN:
                    pass
                    
        except Exception as e:
            print(f"Device error: {e}")
    
    async def broadcast(self, data):
        """Broadcast to all WebSocket clients"""
        if self.clients:
            msg = json.dumps(data)
            await asyncio.gather(
                *[client.send(msg) for client in self.clients],
                return_exceptions=True
            )
    
    async def run(self):
        """Main entry point"""
        devices = self.find_touch_devices()
        
        if not devices:
            print("ERROR: No touch devices found!")
            return
        
        print(f"Starting touch handler with {len(devices)} device(s)")
        print("Touch events will be available at ws://localhost:8765")
        
        # Start WebSocket server
        server = await asyncio.start_server(
            self.handle_client,
            '0.0.0.0',
            8765
        )
        
        async with server:
            await server.serve_forever()
    
    async def handle_client(self, reader, writer):
        """Handle WebSocket client"""
        try:
            # Simple WebSocket handshake
            writer.write(b'HTTP/1.1 101 Switching Protocols\r\n')
            writer.write(b'Upgrade: websocket\r\n')
            writer.write(b'Connection: Upgrade\r\n')
            writer.write(b'Sec-WebSocket-Accept: *\r\n\r\n')
            await writer.drain()
            
            self.clients.add(writer)
            print(f"Client connected. Total: {len(self.clients)}")
            
            # Keep connection alive
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                    
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            self.clients.discard(writer)
            writer.close()

if __name__ == '__main__':
    handler = TouchHandler()
    try:
        asyncio.run(handler.run())
    except KeyboardInterrupt:
        print("\nStopping...")
        sys.exit(0)
