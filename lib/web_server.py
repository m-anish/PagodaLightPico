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
            '/pins': self._page_pins,
            '/windows': self._page_windows,
            '/api/config': self._api_config_get,
            '/api/status': self._api_status_get,
            '/api/pins': self._api_pins_get,
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
        elif path == "/api/pins":
            return self._handle_pins_update(request)
        elif path == "/api/windows":
            return self._handle_windows_update(request)
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
            html += "<a href='/pins'>Add/Remove Controllers</a> | "
            html += "<a href='/windows'>Manage Controllers</a> | "
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
    
    def _page_pins(self):
        """Pin configuration page for managing PWM pins."""
        try:
            from lib.gpio_utils import gpio_utils
            
            html = "<html><head><title>PagodaLight Pin Configuration</title>"
            html += "<style>body{font-family:Arial;margin:15px}table{border-collapse:collapse;width:100%}"
            html += "th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background:#f2f2f2}"
            html += "select,input{padding:4px;border:1px solid #ccc;border-radius:3px;margin:2px}"
            html += "button{background:#007acc;color:white;padding:10px 20px;border:none;cursor:pointer;border-radius:3px;margin:5px}"
            html += ".remove-btn{background:#dc3545}"
            html += "label{font-weight:bold}.note{color:#666;font-size:0.9em}</style>"
            
            html += "<script>"
            html += "function addPinRow(){var table=document.getElementById('pinTable').getElementsByTagName('tbody')[0];"
            html += "var rowCount=table.rows.length;if(rowCount>=5){alert('Maximum 5 PWM pins allowed');return;}"
            html += "var newRow=table.insertRow();newRow.innerHTML=table.rows[0].innerHTML.replace(/pin_\\d+_/g,'pin_'+rowCount+'_');"
            html += "var selects=newRow.getElementsByTagName('select');if(selects.length>0)selects[0].selectedIndex=0;}"
            html += "function removePinRow(btn){var row=btn.closest('tr');if(row.parentNode.children.length>1)row.remove();}"
            html += "</script>"
            
            html += "</head><body>"
            html += "<h1>PWM Pin Configuration</h1>"
            
            try:
                config_data = config_manager.get_config_dict()
                pwm_pins = config_data.get('pwm_pins', {})
                available_pins = gpio_utils.get_available_pins()
                used_pins = set()  # We'll track used pins manually
                
                # Show current pin configuration
                html += "<h3>Current PWM Pins</h3>"
                html += "<table id='currentPins'><tr><th>Pin Number</th><th>Enabled</th><th>Time Windows</th></tr>"
                
                for pin_key, pin_config in pwm_pins.items():
                    if pin_key.startswith('_'):
                        continue  # Skip comment entries
                    enabled = pin_config.get('enabled', False)
                    gpio_pin = pin_config.get('gpio_pin', 'Unknown')
                    pin_name = pin_config.get('name', f'Pin {gpio_pin}')
                    status = 'Yes' if enabled else 'No'
                    time_windows = list(pin_config.get('time_windows', {}).keys())
                    windows_str = ', '.join(time_windows) if time_windows else 'None'
                    html += f"<tr><td>GP{gpio_pin} ({pin_name})</td><td>{status}</td><td>{windows_str}</td></tr>"
                
                html += "</table>"
                
                # Pin configuration form
                html += "<h3>Pin Configuration</h3>"
                html += "<form method='post' action='/api/pins'>"
                html += "<table id='pinTable'><thead><tr><th>Pin</th><th>Enabled</th><th>Action</th></tr></thead><tbody>"
                
                # Show current pins in editable form
                pin_index = 0
                for pin_num, pin_config in pwm_pins.items():
                    enabled = pin_config.get('enabled', False)
                    checked = 'checked' if enabled else ''
                    
                    html += f"<tr><td><select name='pin_{pin_index}_number'>"
                    
                    # Add available pins to dropdown
                    for pin in available_pins:
                        # Include current pin even if it's 'used' by this config
                        if pin == int(pin_num) or pin not in used_pins:
                            selected = 'selected' if pin == int(pin_num) else ''
                            html += f"<option value='{pin}' {selected}>GP{pin}</option>"
                    
                    html += f"</select></td><td><input type='checkbox' name='pin_{pin_index}_enabled' {checked}></td>"
                    html += f"<td><button type='button' class='remove-btn' onclick='removePinRow(this)'>Remove</button></td></tr>"
                    pin_index += 1
                
                # If no pins, add one empty row
                if pin_index == 0:
                    html += f"<tr><td><select name='pin_0_number'>"
                    html += "<option value=''>Select Pin...</option>"
                    for pin in available_pins:
                        if pin not in used_pins:
                            html += f"<option value='{pin}'>GP{pin}</option>"
                    html += "</select></td><td><input type='checkbox' name='pin_0_enabled'></td>"
                    html += "<td><button type='button' class='remove-btn' onclick='removePinRow(this)'>Remove</button></td></tr>"
                
                html += "</tbody></table>"
                
                html += "<p><button type='button' onclick='addPinRow()'>Add Pin</button> "
                html += "<button type='submit'>Save Pin Configuration</button></p>"
                html += "</form>"
                
                html += "<p class='note'><strong>Note:</strong> Maximum 5 PWM pins allowed. "
                html += "Pins used for I2C (GP0, GP1 for RTC) are not available. "
                html += "After changing pins, configure time windows for each pin on the Time Windows page.</p>"
                
            except Exception as e:
                log.error(f"[WEB] Error loading pin config: {e}")
                html += "<p>Error loading pin configuration. Using defaults.</p>"
                html += "<form method='post' action='/api/pins'>"
                html += "<p>Pin: <select name='pin_0_number'><option value='15'>GP15</option></select> "
                html += "Enabled: <input type='checkbox' name='pin_0_enabled' checked></p>"
                html += "<p><button type='submit'>Save</button></p></form>"
            
            html += "<hr><p><a href='/'>Back to Status</a> | <a href='/windows'>Time Windows</a></p>"
            html += "</body></html>"
            
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating pins page: {e}")
            return self._create_html_response("<html><body><h1>Error</h1><p>Could not load pin settings.</p></body></html>")
    
    def _page_windows(self):
        """Controller management page - per-controller time window configuration."""
        try:
            # Force garbage collection before loading page
            gc.collect()
            free_before = gc.mem_free()
            log.debug(f"[WEB] Windows page starting with {free_before} bytes free")
            
            html = "<html><head><title>PagodaLight Controller Management</title>"
            html += "<style>body{font-family:Arial;margin:15px}table{border-collapse:collapse;width:100%}"
            html += "th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background:#f2f2f2}"
            html += "input{padding:4px;border:1px solid #ccc;border-radius:3px;margin:2px}"
            html += "button{background:#007acc;color:white;padding:10px 20px;border:none;cursor:pointer;border-radius:3px;margin:5px}"
            html += ".add-btn{background:#28a745}.remove-btn{background:#dc3545}"
            html += "label{font-weight:bold}.note{color:#666;font-size:0.9em}"
            html += ".controller{border:2px solid #ddd;margin:15px 0;padding:15px;border-radius:8px}"
            html += ".controller h3{margin-top:0;color:#333}"
            html += ".window-row{background:#f9f9f9;margin:5px 0;padding:8px;border-radius:4px}"
            html += "</style>"
            
            # JavaScript for dynamic window management
            html += "<script>"
            html += "function addWindow(pin) {"
            html += "  var container = document.getElementById('windows_' + pin);"
            html += "  var windowCount = container.children.length;"
            html += "  if (windowCount >= 5) { alert('Maximum 5 time windows per controller'); return; }"
            html += "  var newWindow = document.createElement('div');"
            html += "  newWindow.className = 'window-row';"
            html += "  newWindow.innerHTML = '<label>Window Name:</label> <input type=\"text\" name=\"' + pin + '_window_' + windowCount + '_name\" placeholder=\"e.g. morning\"> '"
            html += "    + '<label>Start:</label> <input type=\"time\" name=\"' + pin + '_window_' + windowCount + '_start\"> '"
            html += "    + '<label>End:</label> <input type=\"time\" name=\"' + pin + '_window_' + windowCount + '_end\"> '"
            html += "    + '<label>Duty Cycle (%):</label> <input type=\"number\" name=\"' + pin + '_window_' + windowCount + '_duty_cycle\" min=\"0\" max=\"100\" style=\"width:60px\"> '"
            html += "    + '<button type=\"button\" class=\"remove-btn\" onclick=\"removeWindow(this)\">Remove</button>';"
            html += "  container.appendChild(newWindow);"
            html += "}"
            html += "function removeWindow(btn) { btn.parentElement.remove(); }"
            html += "</script>"
            
            html += "</head><body>"
            html += "<h1>Controller Management</h1>"
            
            try:
                config_data = config_manager.get_config_dict()
                pwm_pins = config_data.get('pwm_pins', {})
                
                # Current sunrise/sunset for reference
                current_time = rtc_module.get_current_time()
                month = current_time[1]
                day = current_time[2]
                sunrise_h, sunrise_m, sunset_h, sunset_m = sun_times_leh.get_sunrise_sunset(month, day)
                
                html += f"<p class='note'><strong>Today's Sunrise:</strong> {sunrise_h:02d}:{sunrise_m:02d} | "
                html += f"<strong>Sunset:</strong> {sunset_h:02d}:{sunset_m:02d}</p>"
                
                if not pwm_pins:
                    html += "<p>No controllers configured. Please <a href='/pins'>add controllers</a> first.</p>"
                else:
                    html += "<form method='post' action='/api/windows'>"
                    
                    # Per-controller configuration
                    for pin_num, pin_config in pwm_pins.items():
                        enabled = pin_config.get('enabled', False)
                        if not enabled:
                            continue  # Skip disabled controllers
                        
                        time_windows = pin_config.get('time_windows', {})
                        
                        html += f"<div class='controller'>"
                        html += f"<h3>Controller GP{pin_num}</h3>"
                        
                        # Show current windows for this controller
                        html += "<h4>Current Time Windows:</h4>"
                        if time_windows:
                            html += "<table><tr><th>Window</th><th>Start</th><th>End</th><th>Duty Cycle</th></tr>"
                            
                            # Always show day window first (calculated from sunrise/sunset)
                            if 'day' in time_windows:
                                day_duty_cycle = time_windows['day'].get('duty_cycle', 80)
                                html += f"<tr><td>Day</td><td>{sunrise_h:02d}:{sunrise_m:02d}</td><td>{sunset_h:02d}:{sunset_m:02d}</td><td>{day_duty_cycle}%</td></tr>"
                            
                            # Show other windows
                            for window_name, window_config in time_windows.items():
                                if window_name == 'day':
                                    continue  # Already shown above
                                
                                start_time = window_config.get('start', '00:00')
                                end_time = window_config.get('end', '00:00')
                                duty_cycle = window_config.get('duty_cycle', 50)
                                display_name = window_name.replace('_', ' ').title()
                                html += f"<tr><td>{display_name}</td><td>{start_time}</td><td>{end_time}</td><td>{duty_cycle}%</td></tr>"
                            
                            html += "</table>"
                        else:
                            html += "<p>No time windows configured for this controller.</p>"
                        
                        # Configuration form for this controller
                        html += "<h4>Configure Time Windows:</h4>"
                        
                        # Day window (always present)
                        day_duty_cycle = time_windows.get('day', {}).get('duty_cycle', 80)
                        html += f"<div class='window-row'>"
                        html += f"<label><strong>Day Window (Sunrise-Sunset):</strong></label> "
                        html += f"<label>Duty Cycle (%):</label> <input type='number' name='{pin_num}_day_duty_cycle' value='{day_duty_cycle}' min='0' max='100' style='width:60px'>"
                        html += "</div>"
                        
                        # Dynamic windows container
                        html += f"<div id='windows_{pin_num}'>"
                        
                        # Existing custom windows for this controller
                        window_index = 0
                        for window_name, window_config in time_windows.items():
                            if window_name == 'day':
                                continue  # Skip day window
                            
                            start_time = window_config.get('start', '')
                            end_time = window_config.get('end', '')
                            duty_cycle = window_config.get('duty_cycle', 50)
                            
                            html += f"<div class='window-row'>"
                            html += f"<label>Window Name:</label> <input type='text' name='{pin_num}_window_{window_index}_name' value='{window_name}' placeholder='e.g. evening'> "
                            html += f"<label>Start:</label> <input type='time' name='{pin_num}_window_{window_index}_start' value='{start_time}'> "
                            html += f"<label>End:</label> <input type='time' name='{pin_num}_window_{window_index}_end' value='{end_time}'> "
                            html += f"<label>Duty Cycle (%):</label> <input type='number' name='{pin_num}_window_{window_index}_duty_cycle' value='{duty_cycle}' min='0' max='100' style='width:60px'> "
                            html += f"<button type='button' class='remove-btn' onclick='removeWindow(this)'>Remove</button>"
                            html += "</div>"
                            window_index += 1
                        
                        html += "</div>"
                        
                        # Add window button for this controller
                        html += f"<button type='button' class='add-btn' onclick='addWindow(\"{pin_num}\")'>Add Time Window</button>"
                        html += "</div>"  # End controller div
                    
                    html += "<p><button type='submit'>Save All Controller Settings</button></p>"
                    html += "</form>"
                    
                    html += "<p class='note'><strong>Note:</strong> Each controller can have up to 5 time windows. "
                    html += "Day windows are automatically calculated from sunrise/sunset times. "
                    html += "Custom windows can span midnight (e.g., 23:00 to 06:00).</p>"
                
            except Exception as e:
                log.error(f"[WEB] Error loading controller config: {e}")
                html += "<p>Error loading controller configuration.</p>"
            
            html += "<hr><p><a href='/'>Back to Status</a> | <a href='/pins'>Add/Remove Controllers</a></p>"
            html += "</body></html>"
            
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating controller management page: {e}")
            return self._create_html_response("<html><body><h1>Error</h1><p>Could not load controller management.</p></body></html>")
    
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
    
    def _api_pins_get(self):
        """API endpoint for pins configuration data."""
        try:
            config_data = config_manager.get_config_dict()
            pins_data = {
                "pwm_pins": config_data.get('pwm_pins', {})
            }
            return self._create_json_response(pins_data)
        except Exception as e:
            log.error(f"[WEB] Error getting pins config: {e}")
            return self._create_json_response({"error": str(e)}, 500)
    
    def _handle_pins_update(self, request):
        """Handle pin configuration update via POST."""
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
                # Parse URL-encoded form data for pins
                update_data = self._parse_pins_form_data(body)
            
            # Update pin configuration
            if config_manager.update_config(update_data):
                log.info("[WEB] Pin configuration updated successfully")
                # Return HTML redirect for form submissions
                if "application/json" not in content_type:
                    return self._create_redirect_response('/pins')
                else:
                    return self._create_json_response({"status": "success", "message": "Pin configuration updated"})
            else:
                if "application/json" not in content_type:
                    return self._create_error_response(500, "Failed to save pin configuration")
                else:
                    return self._create_json_response({"status": "error", "message": "Failed to save pin configuration"}, 500)
                
        except Exception as e:
            log.error(f"[WEB] Error updating pin configuration: {e}")
            # Default to form response on error
            return self._create_error_response(500, str(e))
    
    def _handle_windows_update(self, request):
        """Handle per-controller time window configuration update via POST."""
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
                # Parse URL-encoded form data for windows
                update_data = self._parse_windows_form_data(body)
            
            # Update controller configuration
            if config_manager.update_config(update_data):
                log.info("[WEB] Controller time window configuration updated successfully")
                # Return HTML redirect for form submissions
                if "application/json" not in content_type:
                    return self._create_redirect_response('/windows')
                else:
                    return self._create_json_response({"status": "success", "message": "Controller time windows updated"})
            else:
                if "application/json" not in content_type:
                    return self._create_error_response(500, "Failed to save controller configuration")
                else:
                    return self._create_json_response({"status": "error", "message": "Failed to save controller configuration"}, 500)
                
        except Exception as e:
            log.error(f"[WEB] Error updating controller configuration: {e}")
            # Default to form response on error
            return self._create_error_response(500, str(e))
    
    
    def _parse_windows_form_data(self, body):
        """Parse URL-encoded form data for per-controller time window configuration."""
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
            
            # Build time window configuration from form data
            config_update = {'pwm_pins': {}}
            
            # Group form fields by pin number
            pin_data = {}
            
            # First, identify all pins that have data in the form
            for key, value in form_data.items():
                parts = key.split('_')
                if len(parts) >= 2:
                    pin_number = parts[0]  # First part is the pin number
                    if pin_number not in pin_data:
                        pin_data[pin_number] = {}
            
            # Process day window duty cycle for each pin
            for pin_number in pin_data:
                day_duty_cycle_key = f"{pin_number}_day_duty_cycle"
                if day_duty_cycle_key in form_data:
                    try:
                        duty_cycle = int(form_data[day_duty_cycle_key])
                        pin_data[pin_number]['day'] = {'duty_cycle': duty_cycle}
                    except ValueError:
                        # Default duty_cycle if parsing fails
                        pin_data[pin_number]['day'] = {'duty_cycle': 80}
                else:
                    # Default day window if not in form
                    pin_data[pin_number]['day'] = {'duty_cycle': 80}
            
            # Process custom time windows for each pin
            for pin_number in pin_data:
                # Find all window entries for this pin
                window_data = {}
                
                for key, value in form_data.items():
                    if key.startswith(f"{pin_number}_window_") and "_name" in key:
                        try:
                            # Extract window index from key format: pin_window_X_name
                            parts = key.split('_')
                            if len(parts) >= 4:
                                window_index = parts[2]  # pin_window_INDEX_name
                                window_name = value
                                
                                if not window_name or window_name == '':
                                    continue  # Skip windows with empty names
                                
                                # Get corresponding start/end/duty_cycle for this window
                                start_key = f"{pin_number}_window_{window_index}_start"
                                end_key = f"{pin_number}_window_{window_index}_end"
                                duty_cycle_key = f"{pin_number}_window_{window_index}_duty_cycle"
                                
                                start = form_data.get(start_key, '')
                                end = form_data.get(end_key, '')
                                
                                try:
                                    duty_cycle = int(form_data.get(duty_cycle_key, 50))
                                except ValueError:
                                    duty_cycle = 50  # Default duty_cycle
                                
                                # Only add window if it has valid start/end times
                                if start and end:
                                    window_data[window_name] = {
                                        'start': start,
                                        'end': end,
                                        'duty_cycle': duty_cycle
                                    }
                        except (IndexError, ValueError):
                            continue
                
                # Add all time windows (day + custom) to this pin's configuration
                time_windows = {}
                # Add day window
                if 'day' in pin_data[pin_number]:
                    time_windows['day'] = pin_data[pin_number]['day']
                # Add custom windows
                time_windows.update(window_data)
                
                # Get existing pin configuration to preserve other settings
                try:
                    current_config = config_manager.get_config_dict()
                    existing_pin_config = current_config.get('pwm_pins', {}).get(pin_number, {})
                    # Preserve enabled status and other settings
                    enabled = existing_pin_config.get('enabled', True)
                    
                    # Create updated pin config with new time windows
                    config_update['pwm_pins'][pin_number] = {
                        'enabled': enabled,
                        'time_windows': time_windows
                    }
                except Exception as e:
                    log.error(f"[WEB] Error getting existing pin config: {e}")
                    # Default configuration if we can't get existing
                    config_update['pwm_pins'][pin_number] = {
                        'enabled': True,
                        'time_windows': time_windows
                    }
            
            log.debug(f"[WEB] Parsed windows form data for {len(pin_data)} controllers")
            return config_update
            
        except Exception as e:
            log.error(f"[WEB] Error parsing windows form data: {e}")
            return {}
    
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
    
    def _parse_pins_form_data(self, body):
        """Parse URL-encoded form data for pin configuration."""
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
            
            # Build pin configuration from form data
            pin_config = {'pwm_pins': {}}
            
            # Process pin data - look for pin_X_number and pin_X_enabled patterns
            pin_numbers = {}
            pin_enabled = {}
            
            for key, value in form_data.items():
                if key.startswith('pin_') and key.endswith('_number'):
                    # Extract pin index from key (pin_0_number -> 0)
                    try:
                        pin_index = key.split('_')[1]
                        if value and value != '':
                            pin_numbers[pin_index] = int(value)
                    except (IndexError, ValueError):
                        continue
                elif key.startswith('pin_') and key.endswith('_enabled'):
                    # Extract pin index from key (pin_0_enabled -> 0)
                    try:
                        pin_index = key.split('_')[1]
                        pin_enabled[pin_index] = True  # Checkbox present means enabled
                    except IndexError:
                        continue
            
            # Combine pin numbers with enabled status
            for pin_index in pin_numbers:
                pin_number = pin_numbers[pin_index]
                enabled = pin_enabled.get(pin_index, False)
                pin_key = f"pin_{pin_number}"  # Use pin_XX format
                
                # Get existing time windows for this pin if it exists
                try:
                    current_config = config_manager.get_config_dict()
                    existing_pin_config = current_config.get('pwm_pins', {}).get(pin_key, {})
                    time_windows = existing_pin_config.get('time_windows', {
                        'day': {'duty_cycle': 0},
                        'evening': {'start': '19:00', 'end': '23:00', 'duty_cycle': 30},
                        'night': {'start': '23:00', 'end': '06:00', 'duty_cycle': 10}
                    })
                except:
                    # Default time windows if config can't be loaded
                    time_windows = {
                        'day': {'duty_cycle': 0},
                        'evening': {'start': '19:00', 'end': '23:00', 'duty_cycle': 30},
                        'night': {'start': '23:00', 'end': '06:00', 'duty_cycle': 10}
                    }
                
                pin_config['pwm_pins'][pin_key] = {
                    'name': f'Pin {pin_number}',
                    'gpio_pin': pin_number,
                    'enabled': enabled,
                    'time_windows': time_windows
                }
            
            log.debug(f"[WEB] Parsed pin form data: {pin_config}")
            return pin_config
            
        except Exception as e:
            log.error(f"[WEB] Error parsing pins form data: {e}")
            return {}


# Global web server instance
web_server = ConfigWebServer()
