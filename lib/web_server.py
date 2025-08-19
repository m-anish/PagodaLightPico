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
            log.info(f"Web server started on port {self.port}")
            return True
        except Exception as e:
            log.error(f"Failed to start web server: {e}")
            return False
    
    def stop(self):
        """Stop the web server."""
        self.running = False
        if self.socket:
            self.socket.close()
            log.info("Web server stopped")
    
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
        
        try:
            self.socket.settimeout(timeout)
            conn, addr = self.socket.accept()
            log.debug(f"Connection from {addr}")
            
            try:
                request = conn.recv(1024).decode('utf-8')
                response = self._process_request(request)
                conn.send(response.encode('utf-8'))
                return True
            except Exception as e:
                log.error(f"Error processing request: {e}")
                error_response = self._create_error_response(500, str(e))
                conn.send(error_response.encode('utf-8'))
                return True
            finally:
                conn.close()
                
        except OSError:
            # Timeout occurred, this is normal
            return False
        except Exception as e:
            log.error(f"Error handling request: {e}")
            return False
    
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
        
        log.debug(f"Processing {method} request for {path}")
        
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
                log.info("Configuration updated successfully via web interface")
                return self._create_json_response({"status": "success", "message": "Configuration updated"})
            else:
                return self._create_json_response({"status": "error", "message": "Failed to save configuration"}, 500)
                
        except Exception as e:
            log.error(f"Error updating configuration: {e}")
            return self._create_json_response({"status": "error", "message": str(e)}, 500)
    
    def _create_config_page(self):
        """Create the HTML configuration page."""
        config_data = config_manager.get_config_dict()
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>PagodaLight Configuration</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .section {{ margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
        .section h3 {{ margin-top: 0; color: #333; border-bottom: 2px solid #007acc; padding-bottom: 5px; }}
        .form-group {{ margin-bottom: 15px; }}
        .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        .form-group input, .form-group select {{ width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
        .time-windows {{ display: grid; gap: 15px; }}
        .time-window {{ padding: 15px; border: 1px solid #eee; border-radius: 5px; background: #fafafa; }}
        .time-window h4 {{ margin-top: 0; color: #555; }}
        .time-inputs {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }}
        .btn {{ background-color: #007acc; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }}
        .btn:hover {{ background-color: #005a99; }}
        .status {{ margin-top: 10px; padding: 10px; border-radius: 4px; display: none; }}
        .status.success {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
        .status.error {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
        .readonly {{ background-color: #f8f9fa; }}
        .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .status-card {{ padding: 15px; border-radius: 5px; background: #f8f9fa; border-left: 4px solid #007acc; }}
        .status-value {{ font-size: 1.2em; font-weight: bold; color: #007acc; }}
        .status-label {{ font-size: 0.9em; color: #666; margin-bottom: 5px; }}
        .connection-status {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }}
        .connected {{ background: #d4edda; color: #155724; }}
        .disconnected {{ background: #f8d7da; color: #721c24; }}
        .refresh-info {{ font-size: 0.8em; color: #666; text-align: center; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏯 PagodaLight Configuration</h1>
        <p>Configure your meditation center lighting system settings below.</p>
        
        <div class="section">
            <h3>📊 System Status</h3>
            <div id="systemStatus" class="status-grid">
                <div class="status-card">
                    <div class="status-label">LED Status</div>
                    <div class="status-value" id="ledStatus">Loading...</div>
                </div>
                <div class="status-card">
                    <div class="status-label">Current Time</div>
                    <div class="status-value" id="currentTime">Loading...</div>
                </div>
                <div class="status-card">
                    <div class="status-label">Active Window</div>
                    <div class="status-value" id="activeWindow">Loading...</div>
                </div>
                <div class="status-card">
                    <div class="status-label">Window Times</div>
                    <div class="status-value" id="windowTimes">Loading...</div>
                </div>
                <div class="status-card">
                    <div class="status-label">System Uptime</div>
                    <div class="status-value" id="systemUptime">Loading...</div>
                </div>
                <div class="status-card">
                    <div class="status-label">Connections</div>
                    <div class="status-value">
                        <span id="wifiStatus" class="connection-status">WiFi</span>
                        <span id="mqttStatus" class="connection-status">MQTT</span>
                    </div>
                </div>
            </div>
            <div class="refresh-info">Status updates every 60 seconds</div>
        </div>
        
        <form id="configForm">
            <div class="section">
                <h3>📶 WiFi Settings</h3>
                <div class="form-group">
                    <label for="wifi_ssid">Network Name (SSID):</label>
                    <input type="text" id="wifi_ssid" name="wifi_ssid" value="{config_data.get('wifi', {}).get('ssid', '')}" required>
                </div>
                <div class="form-group">
                    <label for="wifi_password">Password:</label>
                    <input type="password" id="wifi_password" name="wifi_password" value="{config_data.get('wifi', {}).get('password', '')}" required>
                </div>
            </div>
            
            <div class="section">
                <h3>🌍 Timezone Settings</h3>
                <div class="form-group">
                    <label for="timezone_name">Timezone Name:</label>
                    <input type="text" id="timezone_name" name="timezone_name" value="{config_data.get('timezone', {}).get('name', 'UTC')}" required>
                </div>
                <div class="form-group">
                    <label for="timezone_offset">UTC Offset (hours):</label>
                    <input type="number" id="timezone_offset" name="timezone_offset" step="0.5" min="-12" max="14" value="{config_data.get('timezone', {}).get('offset', 0)}" required>
                </div>
            </div>
            
            <div class="section">
                <h3>🔧 Hardware Settings</h3>
                <div class="form-group">
                    <label for="led_pwm_pin">LED PWM Pin:</label>
                    <input type="number" id="led_pwm_pin" name="led_pwm_pin" min="0" max="28" value="{config_data.get('hardware', {}).get('led_pwm_pin', 16)}" required>
                </div>
                <div class="form-group">
                    <label for="pwm_frequency">PWM Frequency (Hz):</label>
                    <input type="number" id="pwm_frequency" name="pwm_frequency" min="1" max="40000000" value="{config_data.get('hardware', {}).get('pwm_frequency', 1000)}" required>
                </div>
                <div class="form-group">
                    <label for="rtc_i2c_sda_pin">RTC I2C SDA Pin:</label>
                    <input type="number" id="rtc_i2c_sda_pin" name="rtc_i2c_sda_pin" min="0" max="28" value="{config_data.get('hardware', {}).get('rtc_i2c_sda_pin', 20)}" required>
                </div>
                <div class="form-group">
                    <label for="rtc_i2c_scl_pin">RTC I2C SCL Pin:</label>
                    <input type="number" id="rtc_i2c_scl_pin" name="rtc_i2c_scl_pin" min="0" max="28" value="{config_data.get('hardware', {}).get('rtc_i2c_scl_pin', 21)}" required>
                </div>
            </div>
            
            <div class="section">
                <h3>⚙️ System Settings</h3>
                <div class="form-group">
                    <label for="log_level">Log Level:</label>
                    <select id="log_level" name="log_level" required>
                        <option value="FATAL" {"selected" if config_data.get('system', {}).get('log_level') == 'FATAL' else ""}>FATAL</option>
                        <option value="ERROR" {"selected" if config_data.get('system', {}).get('log_level') == 'ERROR' else ""}>ERROR</option>
                        <option value="WARN" {"selected" if config_data.get('system', {}).get('log_level') == 'WARN' else ""}>WARN</option>
                        <option value="INFO" {"selected" if config_data.get('system', {}).get('log_level') == 'INFO' else ""}>INFO</option>
                        <option value="DEBUG" {"selected" if config_data.get('system', {}).get('log_level') == 'DEBUG' else ""}>DEBUG</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="update_interval">Update Interval (seconds):</label>
                    <input type="number" id="update_interval" name="update_interval" min="1" value="{config_data.get('system', {}).get('update_interval', 60)}" required>
                </div>
            </div>
            
            <div class="section">
                <h3>⏰ Time Windows & LED Control</h3>
                <p><small>Configure different LED brightness levels for different times of day. The "day" window is automatically adjusted based on sunrise/sunset times.</small></p>
                <div class="time-windows">"""
        
        # Add time windows
        time_windows = config_data.get('time_windows', {})
        for window_name, window_config in time_windows.items():
            if window_name.startswith('_'):  # Skip comment fields
                continue
            
            readonly = "readonly class='readonly'" if window_name == "day" else ""
            is_day = window_name == "day"
            
            html += f"""
                    <div class="time-window">
                        <h4>{"🌅 Day (Auto-adjusted)" if is_day else f"🌙 {window_name.replace('_', ' ').title()}"}</h4>
                        {"<small>Start and end times are automatically set based on sunrise/sunset</small>" if is_day else ""}
                        <div class="time-inputs">
                            <div class="form-group">
                                <label for="{window_name}_start">Start Time:</label>
                                <input type="time" id="{window_name}_start" name="{window_name}_start" value="{window_config.get('start', '')}" {readonly} required>
                            </div>
                            <div class="form-group">
                                <label for="{window_name}_end">End Time:</label>
                                <input type="time" id="{window_name}_end" name="{window_name}_end" value="{window_config.get('end', '')}" {readonly} required>
                            </div>
                            <div class="form-group">
                                <label for="{window_name}_duty">Brightness (%):</label>
                                <input type="number" id="{window_name}_duty" name="{window_name}_duty" min="0" max="100" value="{window_config.get('duty_cycle', 0)}" required>
                            </div>
                        </div>
                    </div>"""
        
        html += """
                </div>
            </div>
            
            <button type="submit" class="btn">💾 Save Configuration</button>
            <div id="status" class="status"></div>
        </form>
    </div>
    
    <script>
        document.getElementById('configForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const config = {
                wifi: {
                    ssid: formData.get('wifi_ssid'),
                    password: formData.get('wifi_password')
                },
                timezone: {
                    name: formData.get('timezone_name'),
                    offset: parseFloat(formData.get('timezone_offset'))
                },
                hardware: {
                    led_pwm_pin: parseInt(formData.get('led_pwm_pin')),
                    pwm_frequency: parseInt(formData.get('pwm_frequency')),
                    rtc_i2c_sda_pin: parseInt(formData.get('rtc_i2c_sda_pin')),
                    rtc_i2c_scl_pin: parseInt(formData.get('rtc_i2c_scl_pin'))
                },
                system: {
                    log_level: formData.get('log_level'),
                    update_interval: parseInt(formData.get('update_interval'))
                },
                time_windows: {}
            };
            
            // Add time windows"""
        
        for window_name in time_windows.keys():
            if not window_name.startswith('_'):
                html += f"""
            config.time_windows['{window_name}'] = {{
                start: formData.get('{window_name}_start'),
                end: formData.get('{window_name}_end'),
                duty_cycle: parseInt(formData.get('{window_name}_duty'))
            }};"""
        
        html += """
            
            fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                const status = document.getElementById('status');
                status.style.display = 'block';
                if (data.status === 'success') {
                    status.className = 'status success';
                    status.textContent = '✅ Configuration saved successfully!';
                    setTimeout(() => { status.style.display = 'none'; }, 3000);
                } else {
                    status.className = 'status error';
                    status.textContent = '❌ Error: ' + data.message;
                }
            })
            .catch(error => {
                const status = document.getElementById('status');
                status.style.display = 'block';
                status.className = 'status error';
                status.textContent = '❌ Network error: ' + error.message;
            });
        });
        
        // Status update functionality with 1-minute refresh
        function updateStatus() {
            fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                // Update LED status
                document.getElementById('ledStatus').textContent = 
                    data.led.status + ' (' + data.led.duty_cycle_display + ')';
                
                // Update current time
                document.getElementById('currentTime').textContent = 
                    data.time.current_time + ' ' + data.time.timezone;
                
                // Update active window
                document.getElementById('activeWindow').textContent = 
                    data.time_window.current_display || 'None';
                
                // Update window times
                if (data.time_window.start_time && data.time_window.end_time) {
                    document.getElementById('windowTimes').textContent = 
                        data.time_window.start_time + ' - ' + data.time_window.end_time;
                } else {
                    document.getElementById('windowTimes').textContent = 'N/A';
                }
                
                // Update system uptime
                document.getElementById('systemUptime').textContent = 
                    data.system.uptime_string;
                
                // Update connection status
                const wifiStatus = document.getElementById('wifiStatus');
                wifiStatus.className = 'connection-status ' + (data.connections.wifi ? 'connected' : 'disconnected');
                wifiStatus.textContent = 'WiFi ' + (data.connections.wifi ? '✓' : '✗');
                
                const mqttStatus = document.getElementById('mqttStatus');
                mqttStatus.className = 'connection-status ' + (data.connections.mqtt ? 'connected' : 'disconnected');
                mqttStatus.textContent = 'MQTT ' + (data.connections.mqtt ? '✓' : '✗');
            })
            .catch(error => {
                console.error('Error fetching status:', error);
                // Show error state in status cards
                document.getElementById('ledStatus').textContent = 'Error loading';
                document.getElementById('currentTime').textContent = 'Error loading';
                document.getElementById('activeWindow').textContent = 'Error loading';
                document.getElementById('windowTimes').textContent = 'Error loading';
                document.getElementById('systemUptime').textContent = 'Error loading';
            });
        }
        
        // Initial status load
        updateStatus();
        
        // Set up 1-minute refresh interval (60000 ms)
        setInterval(updateStatus, 60000);
    </script>
</body>
</html>"""
        
        return self._create_html_response(html)
    
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
