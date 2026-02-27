#!/usr/bin/env python3
"""Simple WebSocket test server."""
import asyncio

async def echo(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Client connected: {addr}")
    
    data = await reader.read(1024)
    print(f"Request: {data[:200]}")
    
    # HTTP 101 response
    response = b"""HTTP/1.1 101 Switching Protocols\r
Upgrade: websocket\r
Connection: Upgrade\r
\r
"""
    writer.write(response)
    await writer.drain()
    
    print("Sent 101 Switching Protocols")
    
    # Keep alive
    try:
        while True:
            data = await reader.read(1)
            if not data:
                break
    except:
        pass
    
    print(f"Client {addr} disconnected")
    writer.close()

async def main():
    server = await asyncio.start_server(echo, '0.0.0.0', 8765)
    print("WS Server started on ws://localhost:8765")
    print("Waiting for connections...")
    
    async with server:
        await server.serve_forever()

asyncio.run(main())
