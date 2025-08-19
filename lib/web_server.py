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
            # For memory efficiency, send response directly without encoding everything at once
            chunk_size = 512  # Smaller chunks to reduce memory usage
            response_len = len(response)
            
            # Send in smaller chunks
            for i in range(0, response_len, chunk_size):
                chunk = response[i:i + chunk_size]
                conn.send(chunk.encode('utf-8'))
                # Small delay between chunks to prevent overwhelming the Pico W
                time.sleep(0.005)  # Reduced delay for better performance
                
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
        # Simplified routing table to reduce memory usage
        routes = {
            '/': self._page_status,
            '/config': self._page_config,
            '/system': self._page_system,
            '/pins': self._page_pins,
            '/windows': self._page_windows,
            '/notifications': self._page_notifications,
            '/upload': self._page_upload,
            '/api/config': self._api_config_get,
            '/api/status': self._api_status_get,
            '/api/download': self._api_download_config,
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
        elif path == "/api/notifications":
            return self._handle_notifications_update(request)
        elif path == "/api/upload":
            return self._handle_config_upload(request)
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
        """Simplified status page to reduce memory usage."""
        try:
            # Force garbage collection before generating page
            gc.collect()
            
            # Build HTML in parts to reduce memory fragmentation
            html_parts = [
                "<html><head><title>PagodaLight</title>",
                "<style>body{font-family:Arial;margin:15px}</style></head><body>",
                "<h1>PagodaLight</h1>"
            ]
            
            # Current time - simplified
            try:
                current_time = rtc_module.get_current_time()
                hour = current_time[3]
                minute = current_time[4]
                html_parts.append(f"<p><strong>Time:</strong> {hour:02d}:{minute:02d}</p>")
            except:
                html_parts.append("<p><strong>Time:</strong> Unknown</p>")
            
            # Simplified status - just basic info
            try:
                config_data = config_manager.get_config_dict()
                pwm_pins = config_data.get('pwm_pins', {})
                pin_count = len([k for k in pwm_pins.keys() if not k.startswith('_')])
                html_parts.append(f"<p><strong>Controllers:</strong> {pin_count} configured</p>")
            except:
                html_parts.append("<p><strong>Controllers:</strong> Unknown</p>")
            
            # Memory info
            try:
                gc.collect()
                free_memory = gc.mem_free()
                html_parts.append(f"<p><strong>Memory:</strong> {free_memory} bytes free</p>")
            except:
                html_parts.append("<p><strong>Memory:</strong> Unknown</p>")
            
            # Simplified navigation - removed System Settings to reduce memory usage
            html_parts.extend([
                "<hr><p><a href='/config'>WiFi Config</a> | ",
                "<a href='/pins'>Add/Remove Controllers</a> | ",
                "<a href='/windows'>Manage Controllers</a> | ",
                "<a href='/api/download'>Download Config</a></p>",
                "</body></html>"
            ])
            
            # Join all parts at once to minimize memory fragmentation
            html = "".join(html_parts)
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating status page: {e}")
            return self._create_html_response("<html><body><h1>PagodaLight</h1><p>Error loading status</p></body></html>")
    
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
                # HTML escape the SSID value to handle special characters
                ssid_escaped = self._html_escape(ssid)
                html += f"<p><label>Network Name (SSID):</label><input name='ssid' value='{ssid_escaped}' required></p>"
            except Exception as e:
                log.error(f"[WEB] Error loading SSID from config: {e}")
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
            
            # Build HTML in chunks to reduce memory usage
            html_parts = []
            
            # Header section
            html_parts.extend([
                "<html><head><title>PagodaLight Pin Configuration</title>",
                "<style>body{font-family:Arial;margin:15px}table{border-collapse:collapse;width:100%}",
                "th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background:#f2f2f2}",
                "select,input{padding:4px;border:1px solid #ccc;border-radius:3px;margin:2px}",
                "button{background:#007acc;color:white;padding:10px 20px;border:none;cursor:pointer;border-radius:3px;margin:5px}",
                ".remove-btn{background:#dc3545}",
                "label{font-weight:bold}.note{color:#666;font-size:0.9em}</style>",
                "<script>",
                "function addPinRow(){var table=document.getElementById('pinTable').getElementsByTagName('tbody')[0];",
                "var rowCount=table.rows.length;if(rowCount>=5){alert('Maximum 5 PWM pins allowed');return;}",
                "var newRow=table.insertRow();",
                "newRow.innerHTML='<td><select name=\"pin_'+rowCount+'_number\"><option value=\"\">Select Pin...</option>"
            ])
            
            # Add pin options to JavaScript
            try:
                pin_options = gpio_utils.get_pin_options_for_dropdown(exclude_current_usage=False)
                for pin_num, display_name in pin_options:
                    html_parts.append(f"<option value=\"{pin_num}\">GP{pin_num}</option>")
            except:
                # Fallback to all PWM-capable pins if gpio_utils not available
                all_pins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 25, 26, 27, 28]
                for pin in all_pins:
                    html_parts.append(f"<option value=\"{pin}\">GP{pin}</option>")
            
            # Continue with JavaScript
            html_parts.extend([
                "</select></td><td><input type=\"checkbox\" name=\"pin_'+rowCount+'_enabled\"></td>",
                "<td><button type=\"button\" class=\"remove-btn\" onclick=\"removePinRow(this)\">Remove</button></td>';",
                "}",
                "function removePinRow(btn){var row=btn.closest('tr');row.remove();}",
                "</script>",
                "</head><body>",
                "<h1>PWM Pin Configuration</h1>"
            ])
            
            try:
                config_data = config_manager.get_config_dict()
                pwm_pins = config_data.get('pwm_pins', {})
                available_pins = gpio_utils.get_available_pins()
                used_pins = set()  # We'll track used pins manually
                
                # Show current pin configuration
                html_parts.extend([
                    "<h3>Current PWM Pins</h3>",
                    "<table id='currentPins'><tr><th>Pin Number</th><th>Enabled</th><th>Time Windows</th></tr>"
                ])
                
                for pin_key, pin_config in pwm_pins.items():
                    if pin_key.startswith('_'):
                        continue  # Skip comment entries
                    enabled = pin_config.get('enabled', False)
                    gpio_pin = pin_config.get('gpio_pin', 'Unknown')
                    pin_name = pin_config.get('name', f'Pin {gpio_pin}')
                    status = 'Yes' if enabled else 'No'
                    time_windows = list(pin_config.get('time_windows', {}).keys())
                    windows_str = ', '.join(time_windows) if time_windows else 'None'
                    html_parts.append(f"<tr><td>GP{gpio_pin} ({pin_name})</td><td>{status}</td><td>{windows_str}</td></tr>")
                
                html_parts.append("</table>")
                
                # Pin configuration form
                html_parts.extend([
                    "<h3>Pin Configuration</h3>",
                    "<form method='post' action='/api/pins'>",
                    "<table id='pinTable'><thead><tr><th>Pin</th><th>Enabled</th><th>Action</th></tr></thead><tbody>"
                ])
                
                # Show current pins in editable form
                pin_index = 0
                for pin_key, pin_config in pwm_pins.items():
                    if pin_key.startswith('_'):
                        continue  # Skip comment entries
                    
                    if not isinstance(pin_config, dict):
                        log.error(f"[WEB] Invalid pin config for {pin_key}: expected dict, got {type(pin_config)}")
                        continue
                    
                    enabled = pin_config.get('enabled', False)
                    gpio_pin = pin_config.get('gpio_pin', 0)
                    pin_name = pin_config.get('name', f'Pin {gpio_pin}')
                    checked = 'checked' if enabled else ''
                    
                    # For existing pins, show static text instead of dropdown
                    html_parts.extend([
                        f"<tr><td>GP{gpio_pin} ({pin_name})",
                        f"<input type='hidden' name='pin_{pin_index}_number' value='{gpio_pin}'>",
                        f"</td><td><input type='checkbox' name='pin_{pin_index}_enabled' {checked}></td>",
                        f"<td><button type='button' class='remove-btn' onclick='removePinRow(this)'>Remove</button></td></tr>"
                    ])
                    pin_index += 1
                
                # If no pins, add one empty row
                if pin_index == 0:
                    html_parts.extend([
                        f"<tr><td><select name='pin_0_number'>",
                        "<option value=''>Select Pin...</option>"
                    ])
                    for pin in available_pins:
                        if pin not in used_pins:
                            html_parts.append(f"<option value='{pin}'>GP{pin}</option>")
                    html_parts.extend([
                        "</select></td><td><input type='checkbox' name='pin_0_enabled'></td>",
                        "<td><button type='button' class='remove-btn' onclick='removePinRow(this)'>Remove</button></td></tr>"
                    ])
                
                html_parts.extend([
                    "</tbody></table>",
                    "<p><button type='button' onclick='addPinRow()'>Add Pin</button> ",
                    "<button type='submit'>Save Pin Configuration</button></p>",
                    "</form>",
                    "<p class='note'><strong>Note:</strong> Maximum 5 PWM pins allowed. ",
                    "Pins used for I2C (GP0, GP1 for RTC) are not available. ",
                    "After changing pins, configure time windows for each pin on the Time Windows page.</p>"
                ])
                
            except Exception as e:
                log.error(f"[WEB] Error loading pin config: {e}")
                html_parts.extend([
                    "<p>Error loading pin configuration. Using defaults.</p>",
                    "<form method='post' action='/api/pins'>",
                    "<p>Pin: <select name='pin_0_number'><option value='15'>GP15</option></select> ",
                    "Enabled: <input type='checkbox' name='pin_0_enabled' checked></p>",
                    "<p><button type='submit'>Save</button></p></form>"
                ])
            
            html_parts.extend([
                "<hr><p><a href='/'>Back to Status</a> | <a href='/windows'>Time Windows</a></p>",
                "</body></html>"
            ])
            
            # Join all parts at once to minimize memory fragmentation
            html = "".join(html_parts)
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
            
            # Minimal HTML to reduce memory usage
            html_parts = [
                "<html><head><title>PagodaLight Windows</title>",
                "<style>body{font-family:sans-serif;margin:10px}table{border-collapse:collapse;width:100%;font-size:0.9em}",
                "th,td{border:1px solid #ccc;padding:4px}th{background:#eee}",
                "input{padding:2px;margin:1px;font-size:0.9em;width:80px}",
                "button{background:#007acc;color:white;padding:5px 10px;border:none;cursor:pointer;margin:2px;font-size:0.9em}",
                ".add-btn{background:#28a745}.remove-btn{background:#dc3545}",
                "label{font-weight:bold}.controller{border:1px solid #ccc;margin:10px 0;padding:10px}",
                "</style>",
                "</head><body>",
                "<h1>Time Windows</h1>"
            ]
            
            try:
                config_data = config_manager.get_config_dict()
                pwm_pins = config_data.get('pwm_pins', {})
                
                # Current sunrise/sunset for reference
                current_time = rtc_module.get_current_time()
                month = current_time[1]
                day = current_time[2]
                sunrise_h, sunrise_m, sunset_h, sunset_m = sun_times_leh.get_sunrise_sunset(month, day)
                
                html_parts.extend([
                    f"<p><strong>Sunrise:</strong> {sunrise_h:02d}:{sunrise_m:02d} | ",
                    f"<strong>Sunset:</strong> {sunset_h:02d}:{sunset_m:02d}</p>"
                ])
                
                if not pwm_pins:
                    html_parts.append("<p>No controllers configured. Please <a href='/pins'>add controllers</a> first.</p>")
                else:
                    html_parts.extend([
                        "<form method='post' action='/api/windows'>"
                    ])
                    
                    # Per-controller configuration - simplified
                    for pin_key, pin_config in pwm_pins.items():
                        if pin_key.startswith('_'):
                            continue  # Skip comment entries
                        
                        if not isinstance(pin_config, dict):
                            log.error(f"[WEB] Invalid pin config for {pin_key}: expected dict, got {type(pin_config)}")
                            continue
                        
                        enabled = pin_config.get('enabled', False)
                        if not enabled:
                            continue  # Skip disabled controllers
                        
                        gpio_pin = pin_config.get('gpio_pin', 0)
                        pin_name = pin_config.get('name', f'Pin {gpio_pin}')
                        time_windows = pin_config.get('time_windows', {})
                        
                        html_parts.extend([
                            f"<div class='controller'>",
                            f"<h3>{pin_name} (GP{gpio_pin})</h3>"
                        ])
                        
                        # Day window (always present)
                        day_duty_cycle = time_windows.get('day', {}).get('duty_cycle', 80)
                        html_parts.extend([
                            f"<p><label>Day Window:</label> ",
                            f"<input type='number' name='{pin_key}_day_duty_cycle' value='{day_duty_cycle}' min='0' max='100'>%</p>"
                        ])
                        
                        # Custom windows
                        window_index = 0
                        for window_name, window_config in time_windows.items():
                            if window_name == 'day':
                                continue  # Skip day window
                            
                            start_time = window_config.get('start', '')
                            end_time = window_config.get('end', '')
                            duty_cycle = window_config.get('duty_cycle', 50)
                            
                            html_parts.extend([
                                f"<p><label>{window_name}:</label> ",
                                f"<input type='time' name='{pin_key}_window_{window_index}_start' value='{start_time}'> to ",
                                f"<input type='time' name='{pin_key}_window_{window_index}_end' value='{end_time}'> ",
                                f"<input type='number' name='{pin_key}_window_{window_index}_duty_cycle' value='{duty_cycle}' min='0' max='100'>% ",
                                f"<button type='button' class='remove-btn' onclick='this.parentElement.remove()'>Remove</button></p>"
                            ])
                            window_index += 1
                        
                        html_parts.extend([
                            f"<p><button type='button' class='add-btn' onclick='addWindow(\"{pin_key}\")'>Add Window</button></p>",
                            "</div>"
                        ])
                    
                    html_parts.extend([
                        "<p><button type='submit'>Save</button></p>",
                        "</form>",
                        "<script>",
                        "function addWindow(pin){",
                        "var container=document.querySelector('.controller h3').parentElement;",
                        "var p=document.createElement('p');",
                        "p.innerHTML='<label>New:</label> <input type=\"time\" name=\"'+pin+'_window_new_start\"> to <input type=\"time\" name=\"'+pin+'_window_new_end\"> <input type=\"number\" name=\"'+pin+'_window_new_duty_cycle\" min=\"0\" max=\"100\">% <button type=\"button\" class=\"remove-btn\" onclick=\"this.parentElement.remove()\">Remove</button>';",
                        "container.appendChild(p);",
                        "}",
                        "</script>"
                    ])
                
            except Exception as e:
                log.error(f"[WEB] Error loading controller config: {e}")
                html_parts.append("<p>Error loading controller configuration.</p>")
            
            html_parts.extend([
                "<hr><p><a href='/'>Home</a> | <a href='/pins'>Pins</a></p>",
                "</body></html>"
            ])
            
            # Join all parts at once to minimize memory fragmentation
            html = "".join(html_parts)
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating controller management page: {e}")
            return self._create_html_response("<html><body><h1>Error</h1><p>Could not load controller management.</p></body></html>")
    
    def _page_notifications(self):
        """Push notifications configuration page."""
        try:
            html = "<html><head><title>PagodaLight Push Notifications</title>"
            html += "<style>body{font-family:Arial;margin:15px}select,input{width:100%;padding:8px;margin:5px 0;border:1px solid #ccc;border-radius:3px}"
            html += "button{background:#007acc;color:white;padding:10px 20px;border:none;cursor:pointer;border-radius:3px}"
            html += "label{font-weight:bold}.note{color:#666;font-size:0.9em}</style></head><body>"
            html += "<h1>Push Notifications</h1>"
            html += "<form method='post' action='/api/notifications'>"
            
            try:
                config_data = config_manager.get_config_dict()
                notifications = config_data.get('notifications', {})
                
                enabled = notifications.get('enabled', False)
                broker = notifications.get('mqtt_broker', 'broker.hivemq.com')
                port = notifications.get('mqtt_port', 1883)
                topic = notifications.get('mqtt_topic', 'PagodaLightPico/notifications')
                client_id = notifications.get('mqtt_client_id', 'PagodaLightPico')
                notify_window_change = notifications.get('notify_on_window_change', True)
                notify_errors = notifications.get('notify_on_errors', True)
                
                # Enable/Disable notifications
                checked = 'checked' if enabled else ''
                html += f"<p><label><input type='checkbox' name='enabled' {checked}> Enable Push Notifications</label></p>"
                
                # MQTT Broker settings
                html += f"<p><label>MQTT Broker:</label><input name='mqtt_broker' value='{broker}' placeholder='broker.hivemq.com'></p>"
                html += f"<p><label>MQTT Port:</label><input type='number' name='mqtt_port' value='{port}' min='1' max='65535'></p>"
                html += f"<p><label>MQTT Topic:</label><input name='mqtt_topic' value='{topic}' placeholder='PagodaLightPico/notifications'></p>"
                html += f"<p><label>Client ID:</label><input name='mqtt_client_id' value='{client_id}' placeholder='PagodaLightPico'></p>"
                
                # Notification options
                html += "<h3>Notification Options</h3>"
                window_checked = 'checked' if notify_window_change else ''
                error_checked = 'checked' if notify_errors else ''
                html += f"<p><label><input type='checkbox' name='notify_on_window_change' {window_checked}> Notify on time window changes</label></p>"
                html += f"<p><label><input type='checkbox' name='notify_on_errors' {error_checked}> Notify on system errors</label></p>"
                
            except Exception as e:
                log.error(f"[WEB] Error loading notifications config: {e}")
                # Fallback form
                html += "<p><label><input type='checkbox' name='enabled'> Enable Push Notifications</label></p>"
                html += "<p><label>MQTT Broker:</label><input name='mqtt_broker' value='broker.hivemq.com'></p>"
                html += "<p><label>MQTT Port:</label><input type='number' name='mqtt_port' value='1883'></p>"
                html += "<p><label>MQTT Topic:</label><input name='mqtt_topic' value='PagodaLightPico/notifications'></p>"
                html += "<p><label>Client ID:</label><input name='mqtt_client_id' value='PagodaLightPico'></p>"
            
            html += "<p><button type='submit'>Save Notification Settings</button></p>"
            html += "</form>"
            
            html += "<div class='note'>"
            html += "<h3>Setup Instructions</h3>"
            html += "<p><strong>Popular MQTT Services:</strong></p>"
            html += "<ul>"
            html += "<li><strong>HiveMQ:</strong> broker.hivemq.com (port 1883) - Free public broker</li>"
            html += "<li><strong>Eclipse Mosquitto:</strong> test.mosquitto.org (port 1883) - Test broker</li>"
            html += "<li><strong>Home Assistant:</strong> Use your HA MQTT broker IP and credentials</li>"
            html += "</ul>"
            html += "<p><strong>Mobile Apps:</strong></p>"
            html += "<ul>"
            html += "<li><strong>MQTT Dash (Android):</strong> Subscribe to your topic for notifications</li>"
            html += "<li><strong>MQTTool (iOS):</strong> Monitor MQTT messages on your device</li>"
            html += "<li><strong>Pushover:</strong> Use MQTT-to-Pushover bridge for push notifications</li>"
            html += "</ul>"
            html += "</div>"
            
            html += "<hr><p><a href='/'>Back to Status</a></p>"
            html += "</body></html>"
            
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating notifications page: {e}")
            return self._create_html_response("<html><body><h1>Error</h1><p>Could not load notifications settings.</p></body></html>")
    
    def _page_upload(self):
        """Configuration upload page."""
        try:
            html = "<html><head><title>PagodaLight Upload Configuration</title>"
            html += "<style>body{font-family:Arial;margin:15px}input,textarea{width:100%;padding:8px;margin:5px 0;border:1px solid #ccc;border-radius:3px}"
            html += "button{background:#007acc;color:white;padding:10px 20px;border:none;cursor:pointer;border-radius:3px;margin:5px}"
            html += ".danger{background:#dc3545}.note{color:#666;font-size:0.9em;background:#f8f9fa;padding:10px;border-radius:5px;margin:10px 0}"
            html += "textarea{height:300px;font-family:monospace}</style></head><body>"
            html += "<h1>Upload Configuration</h1>"
            
            html += "<div class='note'>"
            html += "<strong>⚠️ Warning:</strong> Uploading a new configuration will completely replace your current settings. "
            html += "Make sure to <a href='/api/download'>download your current configuration</a> as a backup first."
            html += "</div>"
            
            html += "<form method='post' action='/api/upload' enctype='multipart/form-data'>"
            html += "<h3>Method 1: Upload JSON File</h3>"
            html += "<p><input type='file' name='config_file' accept='.json'></p>"
            html += "<p><button type='submit' name='upload_type' value='file'>Upload File</button></p>"
            html += "</form>"
            
            html += "<form method='post' action='/api/upload'>"
            html += "<h3>Method 2: Paste JSON Configuration</h3>"
            html += "<p><textarea name='config_json' placeholder='Paste your JSON configuration here...'></textarea></p>"
            html += "<p><button type='submit' name='upload_type' value='text'>Upload Configuration</button></p>"
            html += "</form>"
            
            html += "<div class='note'>"
            html += "<h3>Configuration Format</h3>"
            html += "<p>The JSON configuration should include all sections: wifi, timezone, hardware, system, notifications, and pwm_pins. "
            html += "Invalid configurations will be rejected with an error message.</p>"
            html += "</div>"
            
            html += "<hr><p><a href='/'>Back to Status</a> | <a href='/api/download'>Download Current Config</a></p>"
            html += "</body></html>"
            
            return self._create_html_response(html)
            
        except Exception as e:
            log.error(f"[WEB] Error creating upload page: {e}")
            return self._create_html_response("<html><body><h1>Error</h1><p>Could not load upload page.</p></body></html>")
    
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
    
    def _api_download_config(self):
        """API endpoint to download configuration as JSON file."""
        try:
            config_data = config_manager.get_config_dict()
            # Use json.dumps without indent parameter for MicroPython compatibility
            json_data = json.dumps(config_data)
            
            # Create HTTP response with file download headers
            response = "HTTP/1.1 200 OK\r\n"
            response += "Content-Type: application/json\r\n"
            response += "Content-Disposition: attachment; filename=\"pagoda_config.json\"\r\n"
            response += f"Content-Length: {len(json_data)}\r\n"
            response += "Connection: close\r\n"
            response += "\r\n"
            response += json_data
            
            return response
            
        except Exception as e:
            log.error(f"[WEB] Error downloading config: {e}")
            return self._create_json_response({"error": str(e)}, 500)
    
    def _handle_notifications_update(self, request):
        """Handle notifications configuration update via POST."""
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
            
            # Parse form data
            update_data = self._parse_notifications_form_data(body)
            
            # Update configuration
            if config_manager.update_config(update_data):
                log.info("[WEB] Notifications configuration updated successfully")
                return self._create_redirect_response('/notifications')
            else:
                return self._create_error_response(500, "Failed to save notifications configuration")
                
        except Exception as e:
            log.error(f"[WEB] Error updating notifications configuration: {e}")
            return self._create_error_response(500, str(e))
    
    def _handle_config_upload(self, request):
        """Handle configuration file upload via POST."""
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
            
            # Parse upload data
            config_data = self._parse_upload_form_data(body)
            
            if not config_data:
                return self._create_error_response(400, "No valid configuration data found")
            
            # Validate and update configuration
            if config_manager.update_config(config_data):
                log.info("[WEB] Configuration uploaded and updated successfully")
                return self._create_redirect_response('/')
            else:
                return self._create_error_response(500, "Failed to save uploaded configuration")
                
        except Exception as e:
            log.error(f"[WEB] Error uploading configuration: {e}")
            return self._create_error_response(500, str(e))
    
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
        # Pre-calculate content length to avoid multiple len() calls
        content_length = len(html)
        response = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: text/html\r\n"
            f"Content-Length: {content_length}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{html}"
        )
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
            
            # Note: Legacy global time_windows configuration has been removed.
            # Time windows are now configured per-controller via the /api/windows endpoint.
            
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


    def _parse_notifications_form_data(self, body):
        """Parse URL-encoded form data for notifications configuration."""
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
            
            # Build notifications configuration from form data
            config_update = {'notifications': {}}
            
            # Handle enabled checkbox
            config_update['notifications']['enabled'] = 'enabled' in form_data
            
            # Handle MQTT settings
            if 'mqtt_broker' in form_data:
                config_update['notifications']['mqtt_broker'] = form_data['mqtt_broker']
            if 'mqtt_port' in form_data:
                try:
                    config_update['notifications']['mqtt_port'] = int(form_data['mqtt_port'])
                except ValueError:
                    config_update['notifications']['mqtt_port'] = 1883
            if 'mqtt_topic' in form_data:
                config_update['notifications']['mqtt_topic'] = form_data['mqtt_topic']
            if 'mqtt_client_id' in form_data:
                config_update['notifications']['mqtt_client_id'] = form_data['mqtt_client_id']
            
            # Handle notification options
            config_update['notifications']['notify_on_window_change'] = 'notify_on_window_change' in form_data
            config_update['notifications']['notify_on_errors'] = 'notify_on_errors' in form_data
            
            log.debug(f"[WEB] Parsed notifications form data: {config_update}")
            return config_update
            
        except Exception as e:
            log.error(f"[WEB] Error parsing notifications form data: {e}")
            return {}
    
    def _parse_upload_form_data(self, body):
        """Parse form data for configuration upload (both file and text)."""
        try:
            # Check if this is multipart form data (file upload)
            if 'Content-Disposition:' in body:
                # Handle multipart form data for file upload
                return self._parse_multipart_upload(body)
            else:
                # Handle regular form data for text upload
                pairs = body.split('&')
                form_data = {}
                
                for pair in pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        # URL decode the key and value
                        key = key.replace('+', ' ').replace('%20', ' ')
                        value = value.replace('+', ' ').replace('%20', ' ')
                        form_data[key] = value
                
                # Get JSON configuration from text area
                if 'config_json' in form_data and form_data['config_json'].strip():
                    try:
                        config_data = json.loads(form_data['config_json'])
                        log.debug("[WEB] Parsed JSON configuration from text upload")
                        return config_data
                    except json.JSONDecodeError as e:
                        log.error(f"[WEB] Invalid JSON in text upload: {e}")
                        return None
                
                return None
                
        except Exception as e:
            log.error(f"[WEB] Error parsing upload form data: {e}")
            return None
    
    def _parse_multipart_upload(self, body):
        """Parse multipart form data for file upload."""
        try:
            # Simple multipart parser for file uploads
            # Look for JSON content between boundaries
            lines = body.split('\n')
            json_content = ""
            in_json = False
            
            for line in lines:
                line = line.strip()
                if line.startswith('Content-Type: application/json') or line.endswith('.json'):
                    in_json = True
                    continue
                elif line.startswith('--') and in_json:
                    # End of this part
                    break
                elif in_json and line and not line.startswith('Content-'):
                    json_content += line
            
            if json_content:
                try:
                    config_data = json.loads(json_content)
                    log.debug("[WEB] Parsed JSON configuration from file upload")
                    return config_data
                except json.JSONDecodeError as e:
                    log.error(f"[WEB] Invalid JSON in file upload: {e}")
                    return None
            
            return None
            
        except Exception as e:
            log.error(f"[WEB] Error parsing multipart upload: {e}")
            return None


    def _html_escape(self, text):
        """Simple HTML escaping for attribute values."""
        if not text:
            return ""
        # Replace common HTML special characters
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        return text


# Global web server instance
web_server = ConfigWebServer()
