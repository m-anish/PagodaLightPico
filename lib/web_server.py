"""
Simple async web server for PagodaLightPico.

Provides basic web interface for system status without complex endpoints.
"""

import asyncio
import socket
import json
from simple_logger import Logger
from lib import config_manager as config
from lib.system_status import system_status
import rtc_module
import time

log = Logger()

class AsyncWebServer:
    """
    Simple async web server for PagodaLightPico.
    Minimal memory footprint with basic functionality.
    """
    
    def __init__(self, port=80):
        self.port = port
        self.running = False
        self.server_socket = None
    
    async def start(self):
        """Start the web server."""
        try:
            log.info(f"[WEB] Starting async web server on port {self.port}")
            
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.setblocking(False)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(1)
            
            self.running = True
            log.info(f"[WEB] Async web server started on port {self.port}")
            return True
            
        except Exception as e:
            log.error(f"[WEB] Failed to start web server: {e}")
            self.running = False
            return False
    
    def stop(self):
        """Stop the web server."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        log.info("[WEB] Web server stopped")
    
    async def serve_forever(self):
        """Main server loop."""
        if not self.running:
            return
            
        log.info("[WEB] Starting server loop")
        
        while self.running:
            try:
                # Accept connections with timeout
                try:
                    client_socket, addr = self.server_socket.accept()
                    client_socket.setblocking(False)
                    log.debug(f"[WEB] Connection from {addr}")
                    
                    # Handle client in separate task
                    asyncio.create_task(self.handle_client(client_socket, addr))
                    
                except OSError:
                    # No connection available, yield control
                    await asyncio.sleep(0.1)
                    continue
                    
            except Exception as e:
                log.error(f"[WEB] Server loop error: {e}")
                await asyncio.sleep(1)
    
    async def handle_client(self, client_socket, addr):
        """Handle a client connection."""
        try:
            # Read request with timeout
            request_data = b""
            start_time = time.time()
            
            while time.time() - start_time < 5:  # 5 second timeout
                try:
                    chunk = client_socket.recv(1024)
                    if not chunk:
                        break
                    request_data += chunk
                    if b'\r\n\r\n' in request_data:
                        break
                except OSError:
                    await asyncio.sleep(0.01)
                    continue
            
            if not request_data:
                return
            
            # Parse request
            try:
                request_str = request_data.decode('utf-8')
            except:
                # If decode fails, try with latin-1 which accepts all byte values
                request_str = request_data.decode('latin-1')
            lines = request_str.split('\r\n')
            if not lines:
                return
                
            request_line = lines[0]
            parts = request_line.split(' ')
            if len(parts) < 2:
                return
                
            method = parts[0]
            path = parts[1]
            
            log.debug(f"[WEB] {method} {path} from {addr}")
            
            # Generate response
            if path == '/':
                response = self.generate_main_page()
            elif path == '/status':
                response = self.generate_status_json()
            else:
                response = self.generate_404()
            
            # Send response
            try:
                client_socket.send(response.encode('utf-8'))
            except OSError:
                pass  # Client disconnected
                
        except Exception as e:
            log.error(f"[WEB] Client handling error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def generate_main_page(self):
        """Generate simple main page."""
        try:
            current_time = rtc_module.get_current_time()
            time_str = f"{current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d}"
            date_str = f"{current_time[2]:02d}/{current_time[1]:02d}/{current_time[0]}"

            status = system_status.get_status_dict()

            html = f"""<!DOCTYPE html>
    <html>
    <head>
        <title>PagodaLightPico</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
            h1 {{ color: #2c3e50; text-align: center; }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .online {{ background: #d4edda; border-left: 4px solid #28a745; }}
            .offline {{ background: #f8d7da; border-left: 4px solid #dc3545; }}
            .time {{ font-size: 24px; text-align: center; margin: 20px 0; color: #2c3e50; }}
        </style>
        <script>
            // Lightweight client-side clock updating every second without server calls
            function startClock(h, m, s) {{
                const timeEl = document.getElementById('time');
                function pad(n) {{ return (n < 10 ? '0' : '') + n; }}
                function tick() {{
                    s += 1;
                    if (s >= 60) {{ s = 0; m += 1; }}
                    if (m >= 60) {{ m = 0; h = (h + 1) %% 24; }}
                    timeEl.textContent = pad(h) + ':' + pad(m) + ':' + pad(s);
                }}
                setInterval(tick, 1000);
            }}
        </script>
    </head>
    <body onload="startClock({current_time[3]}, {current_time[4]}, {current_time[5]})">
        <div class="container">
            <h1>PagodaLightPico</h1>
            <div class="time"><span id="time">{time_str}</span><br><small>{date_str}</small></div>

            <div class="status {'online' if status.get('connections', {}).get('wifi', False) else 'offline'}">
                <strong>WiFi:</strong> {'Connected' if status.get('connections', {}).get('wifi', False) else 'Offline'}
            </div>

            <div class="status {'online' if status.get('connections', {}).get('web_server', False) else 'offline'}">
                <strong>Web Server:</strong> {'Running' if status.get('connections', {}).get('web_server', False) else 'Stopped'}
            </div>

            <div class="status {'online' if status.get('connections', {}).get('mqtt', False) else 'offline'}">
                <strong>MQTT:</strong> {'Connected' if status.get('connections', {}).get('mqtt', False) else 'Offline'}
            </div>

            <p style="text-align: center; margin-top: 30px;">
                <a href="/status" style="color: #007bff;">View JSON Status</a>
            </p>
        </div>
    </body>
    </html>"""

            response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(html)}\r\nConnection: close\r\n\r\n{html}"
            return response

        except Exception as e:
            log.error(f"[WEB] Error generating main page: {e}")
            return self.generate_500()

    def generate_status_json(self):
        """Generate JSON status response."""
        try:
            current_time = rtc_module.get_current_time()
            status = system_status.get_status_dict()
            
            data = {
                'timestamp': time.time(),
                'current_time': {
                    'hour': current_time[3],
                    'minute': current_time[4],
                    'second': current_time[5],
                    'day': current_time[2],
                    'month': current_time[1],
                    'year': current_time[0]
                }
            }
            # Merge the status dictionary into data
            data.update(status)
            
            json_str = json.dumps(data)
            response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\nConnection: close\r\n\r\n{json_str}"
            return response
            
        except Exception as e:
            log.error(f"[WEB] Error generating status JSON: {e}")
            return self.generate_500()
    
    def generate_404(self):
        """Generate 404 response."""
        html = """<!DOCTYPE html>
<html>
<head><title>404 Not Found</title></head>
<body>
    <h1>404 - Page Not Found</h1>
    <p><a href="/">Back to Home</a></p>
</body>
</html>"""
        response = f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nContent-Length: {len(html)}\r\nConnection: close\r\n\r\n{html}"
        return response
    
    def generate_500(self):
        """Generate 500 response."""
        html = """<!DOCTYPE html>
<html>
<head><title>500 Server Error</title></head>
<body>
    <h1>500 - Server Error</h1>
    <p><a href="/">Back to Home</a></p>
</body>
</html>"""
        response = f"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/html\r\nContent-Length: {len(html)}\r\nConnection: close\r\n\r\n{html}"
        return response

# Global web server instance
web_server = AsyncWebServer()