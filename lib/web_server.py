"""
Simple web server module for PagodaLightPico.

Provides a basic HTTP server that serves a static page.
"""

import socket
from simple_logger import Logger

log = Logger()

class ConfigWebServer:
    """
    Simple HTTP server that serves a static page.
    """
    
    def __init__(self, port=80):
        self.port = port
        self.socket = None
        self.running = False
    
    def start(self):
        """Start the web server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('', self.port))
            self.socket.listen(5)
            self.running = True
            log.info(f"[WEB] Server started on port {self.port}")
            return True
        except Exception as e:
            log.error(f"[WEB] Failed to start server: {e}")
            return False
    
    def stop(self):
        """Stop the web server."""
        self.running = False
        if self.socket:
            self.socket.close()
            log.info("[WEB] Server stopped")
    
    def handle_requests(self, timeout=1):
        """
        Handle incoming HTTP requests.
        
        Args:
            timeout (int): Socket timeout in seconds
        
        Returns:
            bool: True if a request was handled, False on timeout
        """
        if not self.running or not self.socket:
            return False
        
        conn = None
        try:
            self.socket.settimeout(timeout)
            conn, addr = self.socket.accept()
            
            try:
                request = conn.recv(1024).decode('utf-8')
                response = self._create_response()
                conn.send(response.encode('utf-8'))
                return True
            except Exception as e:
                log.error(f"[WEB] Error processing request: {e}")
                return True
                
        except OSError:
            # Timeout occurred, this is normal
            return False
        except Exception as e:
            log.error(f"[WEB] Error handling request: {e}")
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
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
        }
    </style>
</head>
<body>
    <h1>PagodaLightPico</h1>
</body>
</html>"""
        
        response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(html)}\r\n\r\n{html}"
        return response

# Global web server instance
web_server = ConfigWebServer()