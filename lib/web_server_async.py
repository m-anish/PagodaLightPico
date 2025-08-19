"""
Async web server module for PagodaLightPico.

Provides an async HTTP server that serves a static page without blocking
other operations in the main loop.
"""

import asyncio
import socket
from simple_logger import Logger

log = Logger()

class AsyncWebServer:
    """
    Async HTTP server that serves a static page.
    """
    
    def __init__(self, port=80):
        self.port = port
        self.server_socket = None
        self.running = False
    
    async def start(self):
        """Start the async web server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('', self.port))
            self.server_socket.listen(5)
            self.server_socket.setblocking(False)  # Non-blocking socket
            self.running = True
            log.info(f"[WEB] Async server started on port {self.port}")
            return True
        except Exception as e:
            log.error(f"[WEB] Failed to start async server: {e}")
            return False
    
    def stop(self):
        """Stop the web server."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            log.info("[WEB] Async server stopped")
    
    async def handle_client(self, client_socket, addr):
        """
        Handle a single client connection asynchronously.
        
        Args:
            client_socket: Client socket connection
            addr: Client address
        """
        try:
            log.debug(f"[WEB] Handling connection from {addr}")
            
            # Set client socket to non-blocking
            client_socket.setblocking(False)
            
            # Read request with timeout
            request_data = b""
            try:
                # Try to read request data
                while True:
                    try:
                        chunk = client_socket.recv(1024)
                        if not chunk:
                            break
                        request_data += chunk
                        # Check if we have a complete HTTP request
                        if b'\r\n\r\n' in request_data or b'\n\n' in request_data:
                            break
                    except OSError as e:
                        if e.errno == 11:  # EAGAIN - no more data available
                            break
                        else:
                            raise
                    
                    # Yield control to prevent blocking
                    await asyncio.sleep(0.001)
            
            except Exception as e:
                log.error(f"[WEB] Error reading request: {e}")
                return
            
            if request_data:
                try:
                    request = request_data.decode('utf-8')
                    response = self._create_response()
                    
                    # Send response asynchronously
                    await self._send_response_async(client_socket, response)
                    
                except Exception as e:
                    log.error(f"[WEB] Error processing request: {e}")
            
        except Exception as e:
            log.error(f"[WEB] Error handling client {addr}: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    async def _send_response_async(self, client_socket, response):
        """
        Send HTTP response asynchronously.
        
        Args:
            client_socket: Client socket
            response (str): HTTP response to send
        """
        try:
            response_bytes = response.encode('utf-8')
            total_sent = 0
            
            while total_sent < len(response_bytes):
                try:
                    sent = client_socket.send(response_bytes[total_sent:])
                    if sent == 0:
                        break
                    total_sent += sent
                except OSError as e:
                    if e.errno == 11:  # EAGAIN - socket buffer full
                        await asyncio.sleep(0.001)  # Brief yield
                        continue
                    else:
                        raise
                
                # Yield control periodically
                if total_sent % 512 == 0:
                    await asyncio.sleep(0.001)
                    
        except Exception as e:
            log.error(f"[WEB] Error sending response: {e}")
            raise
    
    async def serve_forever(self):
        """
        Main server loop that accepts connections asynchronously.
        """
        if not self.running or not self.server_socket:
            log.error("[WEB] Server not properly initialized")
            return
        
        log.info("[WEB] Starting async server loop")
        
        while self.running:
            try:
                # Try to accept a connection (non-blocking)
                try:
                    client_socket, addr = self.server_socket.accept()
                    # Handle client in a separate task
                    asyncio.create_task(self.handle_client(client_socket, addr))
                except OSError as e:
                    if e.errno == 11:  # EAGAIN - no pending connections
                        # No connections available, yield control
                        await asyncio.sleep(0.01)
                        continue
                    else:
                        raise
                
            except Exception as e:
                log.error(f"[WEB] Error in server loop: {e}")
                await asyncio.sleep(0.1)  # Brief pause before retrying
        
        log.info("[WEB] Async server loop ended")
    
    def _create_response(self):
        """Create a simple HTML response."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>PagodaLightPico</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 50px;
            text-align: center;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        .status {
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>PagodaLightPico</h1>
        <p class="status">Async Web Server Running</p>
    </div>
</body>
</html>"""
        
        response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(html)}\r\nConnection: close\r\n\r\n{html}"
        return response