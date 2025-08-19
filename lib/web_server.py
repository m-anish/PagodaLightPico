"""
Web server module for PagodaLightPico configuration interface.

Provides a simple HTTP server running on the Pico W that serves a configuration
management interface for updating system settings at runtime.
"""

import socket
import json
import time
import gc
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
        """Handle GET requests using micro-framework routing."""
        # Simple routing table - easy to extend
        routes = {
            '/': self._page_status,
            '/config': self._page_config,
            '/system': self._page_system,
            '/windows': self._page_windows,
            '/api/config': self._api_config_get,
            '/api/status': self._api_status_get,
        }
        
        handler = routes.get(path)
        if handler:
            return handler()
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
            # Extract body from POST request
            body_start = request.find('\r\n\r\n')
            if body_start == -1:
                body_start = request.find('\n\n')
            
            if body_start == -1:
                return self._create_error_response(400, "No request body")
            
            body = request[body_start + 4:].strip()
            if not body:
                return self._create_error_response(400, "Empty request body")
            
            # Determine content type - JSON or form data
            content_type = "application/x-www-form-urlencoded"  # Default for HTML forms
            if "Content-Type:" in request:
                for line in request.split('\n'):
                    if line.lower().startswith('content-type:'):
                        content_type = line.split(':', 1)[1].strip().lower()
                        break
            
            # Parse update data based on content type
            if "application/json" in content_type:
                try:
                    update_data = json.loads(body)
                except json.JSONDecodeError as e:
                    return self._create_error_response(400, f"Invalid JSON: {e}")
            else:
                # Parse URL-encoded form data
                update_data = self._parse_form_data(body)
            
            # Update configuration
            if config_manager.update_config(update_data):
                log.info("[WEB] Configuration updated successfully")
                # Return HTML redirect for form submissions
                if "application/json" not in content_type:
                    return self._create_redirect_response('/')
                else:
                    return self._create_json_response({"status": "success", "message": "Configuration updated"})
            else:
                if "application/json" not in content_type:
                    return self._create_error_response(500, "Failed to save configuration")
                else:
                    return self._create_json_response({"status": "error", "message": "Failed to save configuration"}, 500)
                
        except Exception as e:
            log.error(f"[WEB] Error updating configuration: {e}")
            # Default to form response on error
            return self._create_error_response(500, str(e))
    
    # ========== PAGE HANDLERS ==========
    
    def _page_status(self):
        """Status page - shows current system state."""
        try:
            html = "<html><head><title>PagodaLight Status</title>"
            html += "<style>body{font-family:Arial;margin:15px}h1{color:#333}p{margin:8px 0}"
            html += "a{color:#007acc;text-decoration:none}.status{background:#f8f9fa;padding:10px;border-radius:5px;margin:10px 0}"
            html += ".led-on{color:#28a745}.led-off{color:#6c757d}</style></head><body>"
            html += "<h1>PagodaLight Status</h1>"
            
            # Current time with day and date
            try:
                current_time = rtc_module.get_current_time()
                # current_time format: (year, month, day, hour, minute, second, weekday, yearday)
                weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                
                weekday = weekdays[current_time[6]] if current_time[6] < 7 else 'Unknown'
                month = months[current_time[1] - 1] if 1 <= current_time[1] <= 12 else 'Unknown'
                day = current_time[2]
                hour = current_time[3]
                minute = current_time[4]
                
                time_str = f"{weekday}, {month} {day}, {hour:02d}:{minute:02d}"
                html += f"<p><strong>Time:</strong> {time_str}</p>"
            except Exception as e:
                log.debug(f"[WEB] Error formatting time: {e}")
                html += "<p><strong>Time:</strong> Unknown</p>"
            
            # LED status with visual indicator
            try:
                duty_cycle = system_status.current_duty_cycle
                status_class = "led-on" if duty_cycle > 0 else "led-off"
                status_text = "ON" if duty_cycle > 0 else "OFF"
                html += f"<p><strong>LED:</strong> <span class='{status_class}'>{status_text} ({duty_cycle}%)</span></p>"
            except:
                html += "<p><strong>LED:</strong> Unknown</p>"
            
            # Current window with fallback logic
            try:
                window = system_status.current_window
                if not window:
                    # Fallback: determine current window based on time
                    try:
                        current_time = rtc_module.get_current_time()
                        current_hour = current_time[3]
                        current_minute = current_time[4]
                        current_time_minutes = current_hour * 60 + current_minute
                        
                        # Get sunrise/sunset times
                        month = current_time[1]
                        day = current_time[2]
                        sunrise_h, sunrise_m, sunset_h, sunset_m = sun_times_leh.get_sunrise_sunset(month, day)
                        sunrise_minutes = sunrise_h * 60 + sunrise_m
                        sunset_minutes = sunset_h * 60 + sunset_m
                        
                        # Check if we're in the day window (sunrise to sunset)
                        if sunrise_minutes <= current_time_minutes <= sunset_minutes:
                            window = "day"
                        else:
                            # Try to determine from config
                            config_data = config_manager.get_config_dict()
                            time_windows = config_data.get('time_windows', {})
                            window = "unknown"  # fallback
                            
                            for window_name, window_config in time_windows.items():
                                if window_name == 'day' or window_name.startswith('_'):
                                    continue
                                
                                start_time = window_config.get('start', '')
                                end_time = window_config.get('end', '')
                                
                                if start_time and end_time:
                                    try:
                                        start_h, start_m = map(int, start_time.split(':'))
                                        end_h, end_m = map(int, end_time.split(':'))
                                        start_minutes = start_h * 60 + start_m
                                        end_minutes = end_h * 60 + end_m
                                        
                                        # Handle overnight windows (end < start)
                                        if end_minutes < start_minutes:
                                            if current_time_minutes >= start_minutes or current_time_minutes <= end_minutes:
                                                window = window_name
                                                break
                                        else:
                                            if start_minutes <= current_time_minutes <= end_minutes:
                                                window = window_name
                                                break
                                    except:
                                        continue
                    except:
                        window = "unknown"
                
                window_display = window.replace('_', ' ').title() if window and window != "unknown" else "Unknown"
                html += f"<p><strong>Window:</strong> {window_display}</p>"
            except:
                html += "<p><strong>Window:</strong> Unknown</p>"
            
            # Window times if available
            try:
                if system_status.current_window_start and system_status.current_window_end:
                    html += f"<p><strong>Times:</strong> {system_status.current_window_start} - {system_status.current_window_end}</p>"
            except:
                pass
            
            # Memory information
            try:
                gc.collect()  # Force garbage collection
                free_memory = gc.mem_free()
                allocated_memory = gc.mem_alloc()
                total_memory = free_memory + allocated_memory
                memory_usage_percent = (allocated_memory / total_memory) * 100
                
                html += f"<p><strong>Memory:</strong> {free_memory} bytes free ({memory_usage_percent:.1f}% used)</p>"
                log.debug(f"[WEB] Memory: {free_memory} free, {allocated_memory} allocated, {memory_usage_percent:.1f}% used")
            except Exception as e:
                log.debug(f"[WEB] Error getting memory info: {e}")
                html += "<p><strong>Memory:</strong> Unknown</p>"
            
            # Navigation links
            html += "<hr><p><a href='/config'>WiFi Config</a> | "
            html += "<a href='/system'>System Settings</a> | "
            html += "<a href='/windows'>Time Windows</a> | "
            html += "<a href='/api/status'>JSON Status</a> | "
            html += "<a href='/api/config'>JSON Config</a></p>"
            html += "</body></html>"
            
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating status page: {e}")
            return self._create_html_response("<html><body><h1>PagodaLight</h1><p>Memory Error</p></body></html>")
    
    def _page_config(self):
        """Configuration page - minimal WiFi settings."""
        try:
            html = "<html><head><title>PagodaLight WiFi Config</title>"
            html += "<style>body{font-family:Arial;margin:15px}input{width:100%;padding:8px;margin:5px 0;border:1px solid #ccc;border-radius:3px}"
            html += "button{background:#007acc;color:white;padding:10px 20px;border:none;cursor:pointer;border-radius:3px}"
            html += "label{font-weight:bold}</style></head><body>"
            html += "<h1>WiFi Configuration</h1>"
            html += "<form method='post' action='/api/config'>"
            
            try:
                config_data = config_manager.get_config_dict()
                ssid = config_data.get('wifi', {}).get('ssid', '')
                html += f"<p><label>Network Name (SSID):</label><input name='ssid' value='{ssid}' required></p>"
            except:
                html += "<p><label>Network Name (SSID):</label><input name='ssid' required></p>"
            
            html += "<p><label>Password:</label><input type='password' name='password' required></p>"
            html += "<p><button type='submit'>Save WiFi Settings</button></p>"
            html += "</form>"
            html += "<hr><p><a href='/'>Back to Status</a></p>"
            html += "</body></html>"
            
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating config page: {e}")
            return self._create_html_response("<html><body><h1>Error</h1><p>Could not load configuration.</p></body></html>")
    
    def _page_system(self):
        """System settings page - log level and update interval."""
        try:
            html = "<html><head><title>PagodaLight System Settings</title>"
            html += "<style>body{font-family:Arial;margin:15px}select,input{width:100%;padding:8px;margin:5px 0;border:1px solid #ccc;border-radius:3px}"
            html += "button{background:#007acc;color:white;padding:10px 20px;border:none;cursor:pointer;border-radius:3px}"
            html += "label{font-weight:bold}</style></head><body>"
            html += "<h1>System Settings</h1>"
            html += "<form method='post' action='/api/config'>"
            
            try:
                config_data = config_manager.get_config_dict()
                current_log = config_data.get('system', {}).get('log_level', 'INFO')
                current_interval = config_data.get('system', {}).get('update_interval', 60)
                
                # Log level selection
                html += "<p><label>Log Level:</label><select name='log_level'>"
                for level in ['FATAL', 'ERROR', 'WARN', 'INFO', 'DEBUG']:
                    selected = 'selected' if level == current_log else ''
                    html += f"<option value='{level}' {selected}>{level}</option>"
                html += "</select></p>"
                
                # Update interval
                html += f"<p><label>Update Interval (seconds):</label><input type='number' name='update_interval' value='{current_interval}' min='10' max='300'></p>"
                
            except:
                # Fallback if config loading fails
                html += "<p><label>Log Level:</label><select name='log_level'>"
                html += "<option value='ERROR'>ERROR</option>"
                html += "<option value='INFO' selected>INFO</option>"
                html += "<option value='DEBUG'>DEBUG</option>"
                html += "</select></p>"
                html += "<p><label>Update Interval (seconds):</label><input type='number' name='update_interval' value='60' min='10' max='300'></p>"
            
            html += "<p><button type='submit'>Save System Settings</button></p>"
            html += "</form>"
            html += "<hr><p><a href='/'>Back to Status</a></p>"
            html += "</body></html>"
            
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating system page: {e}")
            return self._create_html_response("<html><body><h1>Error</h1><p>Could not load system settings.</p></body></html>")
    
    def _page_windows(self):
        """Time window configuration page."""
        try:
            # Force garbage collection before loading page
            gc.collect()
            free_before = gc.mem_free()
            log.debug(f"[WEB] Windows page starting with {free_before} bytes free")
            html = "<html><head><title>PagodaLight Time Windows</title>"
            html += "<style>body{font-family:Arial;margin:15px}table{border-collapse:collapse;width:100%}"
            html += "th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background:#f2f2f2}"
            html += "input{width:60px;padding:4px;border:1px solid #ccc;border-radius:3px}"
            html += "button{background:#007acc;color:white;padding:10px 20px;border:none;cursor:pointer;border-radius:3px;margin:5px}"
            html += "label{font-weight:bold}.note{color:#666;font-size:0.9em}</style></head><body>"
            html += "<h1>Time Window Configuration</h1>"
            
            # Get current configuration
            try:
                config_data = config_manager.get_config_dict()
                time_windows = config_data.get('time_windows', {})
                
                # Current sunrise/sunset for reference
                current_time = rtc_module.get_current_time()
                month = current_time[1]
                day = current_time[2]
                sunrise_h, sunrise_m, sunset_h, sunset_m = sun_times_leh.get_sunrise_sunset(month, day)
                
                html += f"<p class='note'><strong>Today's Sunrise:</strong> {sunrise_h:02d}:{sunrise_m:02d} | "
                html += f"<strong>Sunset:</strong> {sunset_h:02d}:{sunset_m:02d}</p>"
                
                # Table showing existing windows
                html += "<h3>Current Time Windows</h3>"
                html += "<table><tr><th>Window Name</th><th>Start Time</th><th>End Time</th><th>Brightness (%)</th></tr>"
                
                # Day window (always present, calculated from sunrise/sunset)
                html += f"<tr><td>Day</td><td>{sunrise_h:02d}:{sunrise_m:02d}</td><td>{sunset_h:02d}:{sunset_m:02d}</td>"
                day_brightness = time_windows.get('day', {}).get('brightness', 80)
                html += f"<td>{day_brightness}</td></tr>"
                
                # Other windows
                for window_name, config in time_windows.items():
                    try:
                        # Ensure window_name is a string and skip special entries
                        if not isinstance(window_name, str) or window_name == 'day' or window_name.startswith('_'):
                            continue
                        
                        # Ensure config is a dictionary
                        if not isinstance(config, dict):
                            log.debug(f"[WEB] Skipping invalid window config for {window_name}: {type(config)}")
                            continue
                        
                        start_time = config.get('start', '00:00')
                        end_time = config.get('end', '00:00')
                        brightness = config.get('brightness', 50)
                        
                        display_name = window_name.replace('_', ' ').title()
                        html += f"<tr><td>{display_name}</td><td>{start_time}</td><td>{end_time}</td><td>{brightness}</td></tr>"
                    except Exception as window_error:
                        log.error(f"[WEB] Error processing window {window_name}: {window_error}")
                        continue
                
                html += "</table>"
                
                # Form for adding/editing windows
                html += "<h3>Configure Time Windows</h3>"
                html += "<form method='post' action='/api/config'>"
                
                # Day window brightness
                html += "<h4>Day Window Settings</h4>"
                html += f"<p><label>Day Brightness (%):</label> <input type='number' name='day_brightness' value='{day_brightness}' min='0' max='100' style='width:80px'></p>"
                
                # Evening window
                evening_config = time_windows.get('evening', {})
                evening_start = evening_config.get('start', f"{sunset_h:02d}:{sunset_m:02d}")
                evening_end = evening_config.get('end', '23:00')
                evening_brightness = evening_config.get('brightness', 30)
                
                html += "<h4>Evening Window</h4>"
                html += f"<p><label>Start:</label> <input type='time' name='evening_start' value='{evening_start}'> "
                html += f"<label>End:</label> <input type='time' name='evening_end' value='{evening_end}'> "
                html += f"<label>Brightness (%):</label> <input type='number' name='evening_brightness' value='{evening_brightness}' min='0' max='100' style='width:80px'></p>"
                
                # Night window
                night_config = time_windows.get('night', {})
                night_start = night_config.get('start', '23:00')
                night_end = night_config.get('end', f"{sunrise_h:02d}:{sunrise_m:02d}")
                night_brightness = night_config.get('brightness', 10)
                
                html += "<h4>Night Window</h4>"
                html += f"<p><label>Start:</label> <input type='time' name='night_start' value='{night_start}'> "
                html += f"<label>End:</label> <input type='time' name='night_end' value='{night_end}'> "
                html += f"<label>Brightness (%):</label> <input type='number' name='night_brightness' value='{night_brightness}' min='0' max='100' style='width:80px'></p>"
                
                html += "<p><button type='submit'>Save Time Windows</button></p>"
                html += "</form>"
                
                html += "<p class='note'><strong>Note:</strong> Day window times are automatically calculated from sunrise/sunset. "
                html += "Evening and night windows can be customized. Windows spanning midnight (e.g., 23:00 to 06:00) are supported.</p>"
                
            except Exception as e:
                log.error(f"[WEB] Error loading window config: {e}")
                html += "<p>Error loading time window configuration.</p>"
                html += "<form method='post' action='/api/config'>"
                html += "<h4>Day Brightness</h4>"
                html += "<p><label>Brightness (%):</label> <input type='number' name='day_brightness' value='80' min='0' max='100'></p>"
                html += "<p><button type='submit'>Save</button></p>"
                html += "</form>"
            
            html += "<hr><p><a href='/'>Back to Status</a></p>"
            html += "</body></html>"
            
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating windows page: {e}")
            return self._create_html_response("<html><body><h1>Error</h1><p>Could not load time window settings.</p></body></html>")
    
    # ========== API HANDLERS ==========
    
    def _api_status_get(self):
        """API endpoint for status data."""
        try:
            return self._create_json_response(system_status.get_status_dict())
        except Exception as e:
            log.error(f"[WEB] Error getting status: {e}")
            return self._create_json_response({"error": str(e)}, 500)
    
    def _api_config_get(self):
        """API endpoint for configuration data."""
        try:
            return self._create_json_response(config_manager.get_config_dict())
        except Exception as e:
            log.error(f"[WEB] Error getting config: {e}")
            return self._create_json_response({"error": str(e)}, 500)
    
    # ========== LEGACY METHODS (for compatibility) ==========
    
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
    
    def _create_redirect_response(self, location):
        """Create HTTP redirect response."""
        response = f"HTTP/1.1 302 Found\r\n"
        response += f"Location: {location}\r\n"
        response += f"Content-Length: 0\r\n"
        response += f"Connection: close\r\n"
        response += f"\r\n"
        return response
    
    def _parse_form_data(self, body):
        """Parse URL-encoded form data into configuration format."""
        try:
            # Parse URL-encoded data (key=value&key2=value2)
            pairs = body.split('&')
            form_data = {}
            
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    # URL decode the key and value
                    key = key.replace('+', ' ').replace('%20', ' ')
                    value = value.replace('+', ' ').replace('%20', ' ')
                    form_data[key] = value
            
            # Convert form data to configuration structure
            config_update = {}
            
            # Handle WiFi settings
            if 'ssid' in form_data or 'password' in form_data:
                config_update['wifi'] = {}
                if 'ssid' in form_data:
                    config_update['wifi']['ssid'] = form_data['ssid']
                if 'password' in form_data:
                    config_update['wifi']['password'] = form_data['password']
            
            # Handle system settings
            if 'log_level' in form_data or 'update_interval' in form_data:
                config_update['system'] = {}
                if 'log_level' in form_data:
                    config_update['system']['log_level'] = form_data['log_level']
                if 'update_interval' in form_data:
                    try:
                        config_update['system']['update_interval'] = int(form_data['update_interval'])
                    except ValueError:
                        pass  # Skip invalid values
            
            # Handle time window settings
            time_window_fields = ['day_brightness', 'evening_start', 'evening_end', 'evening_brightness',
                                  'night_start', 'night_end', 'night_brightness']
            
            if any(field in form_data for field in time_window_fields):
                config_update['time_windows'] = {}
                
                # Day window
                if 'day_brightness' in form_data:
                    try:
                        brightness = int(form_data['day_brightness'])
                        config_update['time_windows']['day'] = {'brightness': brightness}
                    except ValueError:
                        pass
                
                # Evening window
                evening_fields = ['evening_start', 'evening_end', 'evening_brightness']
                if any(field in form_data for field in evening_fields):
                    evening_config = {}
                    if 'evening_start' in form_data:
                        evening_config['start'] = form_data['evening_start']
                    if 'evening_end' in form_data:
                        evening_config['end'] = form_data['evening_end']
                    if 'evening_brightness' in form_data:
                        try:
                            evening_config['brightness'] = int(form_data['evening_brightness'])
                        except ValueError:
                            pass
                    
                    if evening_config:
                        config_update['time_windows']['evening'] = evening_config
                
                # Night window
                night_fields = ['night_start', 'night_end', 'night_brightness']
                if any(field in form_data for field in night_fields):
                    night_config = {}
                    if 'night_start' in form_data:
                        night_config['start'] = form_data['night_start']
                    if 'night_end' in form_data:
                        night_config['end'] = form_data['night_end']
                    if 'night_brightness' in form_data:
                        try:
                            night_config['brightness'] = int(form_data['night_brightness'])
                        except ValueError:
                            pass
                    
                    if night_config:
                        config_update['time_windows']['night'] = night_config
            
            log.debug(f"[WEB] Parsed form data: {config_update}")
            return config_update
            
        except Exception as e:
            log.error(f"[WEB] Error parsing form data: {e}")
            return {}


# Global web server instance
web_server = ConfigWebServer()
