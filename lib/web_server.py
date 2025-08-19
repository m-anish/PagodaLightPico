"""
Web server module for PagodaLightPico configuration interface.

Provides a simple HTTP server running on the Pico W that serves a configuration
management interface for updating system settings at runtime.
"""

import socket
import json
import time
from lib.config_manager import config_manager
from simple_logger import Logger
import rtc_module
import sun_times_leh
from lib.system_status import system_status

log = Logger()

class ConfigWebServer:
    """
    Simple HTTP server for configuration management interface.
    
    Serves HTML forms for updating configuration and handles POST requests
    to update the configuration in real-time.
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
        Handle incoming HTTP requests with timeout.
        
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
            log.debug(f"[WEB] Connection from {addr}")
            
            # Set connection timeout for send operations
            conn.settimeout(5)  # 5 second timeout for send operations
            
            try:
                request = conn.recv(1024).decode('utf-8')
                response = self._process_request(request)
                
                # Send response in chunks to handle large responses
                self._send_response_chunked(conn, response)
                return True
            except Exception as e:
                log.error(f"[WEB] Error processing request: {e}")
                try:
                    error_response = self._create_error_response(500, str(e))
                    conn.send(error_response.encode('utf-8'))
                except:
                    # If we can't send error response, just log it
                    log.error(f"[WEB] Failed to send error response")
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
    
    def _send_response_chunked(self, conn, response):
        """
        Send HTTP response in chunks to handle large responses.
        
        Args:
            conn: Socket connection
            response (str): HTTP response to send
        """
        try:
            response_bytes = response.encode('utf-8')
            chunk_size = 1024  # Send in 1KB chunks
            
            for i in range(0, len(response_bytes), chunk_size):
                chunk = response_bytes[i:i + chunk_size]
                conn.send(chunk)
                # Small delay between chunks to prevent overwhelming the Pico W
                time.sleep(0.01)
                
        except Exception as e:
            log.error(f"[WEB] Error sending chunked response: {e}")
            raise
    
    def _process_request(self, request):
        """Process HTTP request and return response."""
        lines = request.split('\n')
        if not lines:
            return self._create_error_response(400, "Bad Request")
        
        request_line = lines[0].strip()
        parts = request_line.split(' ')
        
        if len(parts) < 2:
            return self._create_error_response(400, "Bad Request")
        
        method = parts[0]
        path = parts[1]
        
        log.debug(f"[WEB] Processing {method} request for {path}")
        
        if method == "GET":
            return self._handle_get(path)
        elif method == "POST":
            return self._handle_post(path, request)
        else:
            return self._create_error_response(405, "Method Not Allowed")
    
    def _handle_get(self, path):
        """Handle GET requests."""
        if path == "/" or path == "/config":
            return self._create_config_page()
        elif path == "/api/config":
            return self._create_json_response(config_manager.get_config_dict())
        elif path == "/api/status":
            return self._create_json_response(system_status.get_status_dict())
        else:
            return self._create_error_response(404, "Not Found")
    
    def _handle_post(self, path, request):
        """Handle POST requests."""
        if path == "/api/config":
            return self._handle_config_update(request)
        else:
            return self._create_error_response(404, "Not Found")
    
    def _handle_config_update(self, request):
        """Handle configuration update via POST."""
        try:
            # Extract JSON data from POST request
            body_start = request.find('\r\n\r\n')
            if body_start == -1:
                body_start = request.find('\n\n')
            
            if body_start == -1:
                return self._create_error_response(400, "No request body")
            
            body = request[body_start + 4:].strip()
            if not body:
                return self._create_error_response(400, "Empty request body")
            
            # Parse JSON update data
            try:
                update_data = json.loads(body)
            except json.JSONDecodeError as e:
                return self._create_error_response(400, f"Invalid JSON: {e}")
            
            # Update configuration
            if config_manager.update_config(update_data):
                log.info("[WEB] Configuration updated successfully")
                return self._create_json_response({"status": "success", "message": "Configuration updated"})
            else:
                return self._create_json_response({"status": "error", "message": "Failed to save configuration"}, 500)
                
        except Exception as e:
            log.error(f"[WEB] Error updating configuration: {e}")
            return self._create_json_response({"status": "error", "message": str(e)}, 500)
    
    def _create_config_page(self):
        """Create ultra-lightweight HTML configuration page."""
        try:
            config_data = config_manager.get_config_dict()
            
            # Create extremely minimal HTML to avoid memory allocation failures
            html = """<!DOCTYPE html><html><head><title>PagodaLight</title>
<style>body{font-family:Arial;margin:10px}input,select{width:100%;padding:5px;margin:5px 0}
.btn{background:#007acc;color:white;padding:10px;border:none;cursor:pointer}</style>
</head><body><h1>PagodaLight Config</h1><form action="/api/config" method="post">
<h3>WiFi</h3><label>SSID:</label><input name="ssid" value="""
            
            # Add only essential fields to minimize memory usage
            html += config_data.get('wifi', {}).get('ssid', '')
            html += '" required><label>Password:</label><input type="password" name="password" value="'
            html += config_data.get('wifi', {}).get('password', '')
            html += '" required><h3>System</h3><label>Log Level:</label><select name="log_level">'
            
            current_log = config_data.get('system', {}).get('log_level', 'INFO')
            for level in ['ERROR', 'INFO', 'DEBUG']:
                selected = 'selected' if level == current_log else ''
                html += f'<option value="{level}" {selected}>{level}</option>'
            
            html += '</select><h3>Time Windows</h3>'
            
            # Add time windows with minimal formatting
            time_windows = config_data.get('time_windows', {})
            for window_name, window_config in time_windows.items():
                if not window_name.startswith('_'):
                    display_name = window_name.replace('_', ' ').title() if window_name != 'day' else 'Day (Auto)'
                    readonly = 'readonly' if window_name == 'day' else ''
                    html += f'<h4>{display_name}</h4>'
                    html += f'<label>Start:</label><input type="time" name="{window_name}_start" value="{window_config.get("start", "")}" {readonly}>'
                    html += f'<label>End:</label><input type="time" name="{window_name}_end" value="{window_config.get("end", "")}" {readonly}>'
                    html += f'<label>Brightness %:</label><input type="number" name="{window_name}_duty" value="{window_config.get("duty_cycle", 0)}" min="0" max="100">'
            
            html += '<br><button type="submit" class="btn">Save Config</button></form></body></html>'
            
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating config page: {e}")
            # Return minimal error page
            return self._create_html_response("<html><body><h1>Error</h1><p>Memory allocation failed. Please try refreshing.</p></body></html>")
    
    def _create_html_response(self, html):
        """Create HTTP response with HTML content."""
        response = f"HTTP/1.1 200 OK\r\n"
        response += f"Content-Type: text/html\r\n"
        response += f"Content-Length: {len(html)}\r\n"
        response += f"Connection: close\r\n"
        response += f"\r\n"
        response += html
        return response
    
    def _create_json_response(self, data, status_code=200):
        """Create HTTP response with JSON content."""
        status_text = "OK" if status_code == 200 else "Error"
        json_data = json.dumps(data)
        
        response = f"HTTP/1.1 {status_code} {status_text}\r\n"
        response += f"Content-Type: application/json\r\n"
        response += f"Content-Length: {len(json_data)}\r\n"
        response += f"Connection: close\r\n"
        response += f"\r\n"
        response += json_data
        return response
    
    def _create_error_response(self, status_code, message):
        """Create HTTP error response."""
        html = f"""<!DOCTYPE html>
<html>
<head><title>Error {status_code}</title></head>
<body><h1>Error {status_code}</h1><p>{message}</p></body>
</html>"""
        
        response = f"HTTP/1.1 {status_code} {message}\r\n"
        response += f"Content-Type: text/html\r\n"
        response += f"Content-Length: {len(html)}\r\n"
        response += f"Connection: close\r\n"
        response += f"\r\n"
        response += html
        return response


# Global web server instance
web_server = ConfigWebServer()
