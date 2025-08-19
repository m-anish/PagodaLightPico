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
        if path == "/":
            return self._create_config_page()  # Status page by default
        elif path == "/config":
            return self._create_minimal_config_page()  # Minimal config form
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
        """Create minimal status-only page for severe memory constraints."""
        try:
            # Create absolute minimal HTML - no configuration form
            html = "<html><body><h1>PagodaLight Status</h1>"
            
            # Get basic status without complex operations
            try:
                # Get current time safely
                current_time = rtc_module.get_current_time()
                html += f"<p>Time: {current_time[3]:02d}:{current_time[4]:02d}</p>"
            except:
                html += "<p>Time: Unknown</p>"
            
            # Get LED status safely
            try:
                duty_cycle = system_status.current_duty_cycle
                html += f"<p>LED: {duty_cycle}%</p>"
            except:
                html += "<p>LED: Unknown</p>"
            
            # Get current window safely
            try:
                window = system_status.current_window or "None"
                html += f"<p>Window: {window}</p>"
            except:
                html += "<p>Window: Unknown</p>"
            
            html += "<p><a href='/api/status'>JSON Status</a></p>"
            html += "<p><a href='/config'>Try Config</a></p>"
            html += "</body></html>"
            
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating status page: {e}")
            # Return absolute minimal error page
            return self._create_html_response("<html><body><h1>PagodaLight</h1><p>Memory Error</p></body></html>")
    
    def _create_minimal_config_page(self):
        """Create minimal config page - only if specifically requested."""
        try:
            # Only show WiFi config to minimize memory usage
            html = "<html><body><h1>WiFi Config</h1><form method='post' action='/api/config'>"
            
            try:
                config_data = config_manager.get_config_dict()
                ssid = config_data.get('wifi', {}).get('ssid', '')
                html += f"<p>SSID: <input name='ssid' value='{ssid}'></p>"
                html += "<p>Pass: <input type='password' name='password'></p>"
            except:
                html += "<p>SSID: <input name='ssid'></p>"
                html += "<p>Pass: <input type='password' name='password'></p>"
            
            html += "<p><button type='submit'>Save</button></p></form></body></html>"
            
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating config page: {e}")
            return self._create_html_response("<html><body><h1>Error</h1></body></html>")
    
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
