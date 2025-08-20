"""
Simple async web server for PagodaLightPico.

Provides basic web interface for system status without complex endpoints.
"""

import asyncio
import socket
import json
import os
from simple_logger import Logger
from lib import config_manager as config
from lib.system_status import system_status
from lib.pwm_control import multi_pwm
import rtc_module
import time
import machine

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
            elif path == '/download-config':
                response = self.generate_config_download()
            elif path == '/upload-config':
                if method == 'GET':
                    response = self.generate_upload_page()
                elif method == 'POST':
                    response = await self.handle_config_upload(request_str)
                else:
                    response = self.generate_404()
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
            
            # Get PWM controller status
            pwm_status = multi_pwm.get_pin_status()
            config_dict = config.config_manager.get_config_dict()
            
            # Build PWM table HTML
            pwm_table_rows = ""
            for pin_key, pin_info in pwm_status.items():
                pin_config = config_dict.get('pwm_pins', {}).get(pin_key, {})
                
                # Get current window info from system status
                current_window = "None"
                window_time = "N/A"
                
                # Check if we have current window info in system status
                status_pins = status.get('pins', {})
                if pin_key in status_pins:
                    status_pin = status_pins[pin_key]
                    current_window = status_pin.get('window_display', 'None')
                    start_time = status_pin.get('window_start', 'N/A')
                    end_time = status_pin.get('window_end', 'N/A')
                    if start_time != 'N/A' and end_time != 'N/A':
                        window_time = f"{start_time} - {end_time}"
                
                duty_percent = pin_info.get('duty_percent', 0)
                active_status = "Active" if duty_percent > 0 else "Inactive"
                status_class = "active" if duty_percent > 0 else "inactive"
                
                pwm_table_rows += f"""
                <tr class="{status_class}">
                    <td>{pin_info['name']}</td>
                    <td>GPIO {pin_info['gpio_pin']}</td>
                    <td>{active_status}</td>
                    <td>{current_window}</td>
                    <td>{window_time}</td>
                    <td>{duty_percent}%</td>
                </tr>"""
            
            if not pwm_table_rows:
                pwm_table_rows = '<tr><td colspan="6" style="text-align: center; color: #666;">No PWM controllers configured</td></tr>'
            
            # Determine MQTT status and styling
            mqtt_enabled = config_dict.get('notifications', {}).get('enabled', False)
            mqtt_connected = status.get('connections', {}).get('mqtt', False)
            
            if not mqtt_enabled:
                mqtt_status = "Disabled"
                mqtt_class = "disabled"
            elif mqtt_connected:
                mqtt_status = "Connected"
                mqtt_class = "online"
            else:
                mqtt_status = "Offline"
                mqtt_class = "offline"

            html = f"""<!DOCTYPE html>
    <html>
    <head>
        <title>PagodaLightPico</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
            h1 {{ color: #2c3e50; text-align: center; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .online {{ background: #d4edda; border-left: 4px solid #28a745; }}
            .offline {{ background: #f8d7da; border-left: 4px solid #dc3545; }}
            .disabled {{ background: #fff3cd; border-left: 4px solid #ffc107; }}
            .time {{ font-size: 24px; text-align: center; margin: 20px 0; color: #2c3e50; }}
            .pwm-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            .pwm-table th, .pwm-table td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .pwm-table th {{ background-color: #f8f9fa; font-weight: bold; }}
            .pwm-table tr.active {{ background-color: #d4edda; }}
            .pwm-table tr.inactive {{ background-color: #f8f9fa; }}
            .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
            .footer a {{ color: #007bff; text-decoration: none; margin: 0 10px; }}
            .footer a:hover {{ text-decoration: underline; }}
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

            <div class="status {mqtt_class}">
                <strong>MQTT:</strong> {mqtt_status}
            </div>

            <h2>PWM Controllers</h2>
            <table class="pwm-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Pin</th>
                        <th>Status</th>
                        <th>Current Window</th>
                        <th>Window Time</th>
                        <th>Duty Cycle</th>
                    </tr>
                </thead>
                <tbody>
                    {pwm_table_rows}
                </tbody>
            </table>

            <div class="footer">
                <a href="/status">View JSON Status</a>
                <a href="/download-config">Download Config</a>
                <a href="/upload-config">Upload Config</a>
            </div>
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
    
    def generate_config_download(self):
        """Generate config.json download response."""
        try:
            # Read current config file
            with open('config.json', 'r') as f:
                config_content = f.read()
            
            # Generate download response with proper headers
            response = f"""HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Disposition: attachment; filename="config.json"\r\nContent-Length: {len(config_content)}\r\nConnection: close\r\n\r\n{config_content}"""
            return response
            
        except Exception as e:
            log.error(f"[WEB] Error generating config download: {e}")
            return self.generate_500()
    
    def generate_upload_page(self):
        """Generate config upload page."""
        try:
            html = """<!DOCTYPE html>
<html>
<head>
    <title>Upload Config - PagodaLightPico</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #2c3e50; text-align: center; }
        .form-group { margin: 20px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="file"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .btn-secondary { background: #6c757d; }
        .btn-secondary:hover { background: #545b62; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; margin: 20px 0; }
        .footer { text-align: center; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Upload Configuration</h1>
        
        <div class="warning">
            <strong>Warning:</strong> Uploading a new configuration will replace the current settings and trigger a soft reboot. 
            Make sure your configuration is valid to avoid system issues.
        </div>
        
        <form method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label for="config-file">Select config.json file:</label>
                <input type="file" id="config-file" name="config" accept=".json" required>
            </div>
            
            <div class="form-group">
                <button type="submit" class="btn">Upload and Apply</button>
                <a href="/" class="btn btn-secondary" style="text-decoration: none; margin-left: 10px;">Cancel</a>
            </div>
        </form>
        
        <div class="footer">
            <p><a href="/download-config">Download Current Config</a> | <a href="/">Back to Home</a></p>
        </div>
    </div>
</body>
</html>"""
            
            response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(html)}\r\nConnection: close\r\n\r\n{html}"
            return response
            
        except Exception as e:
            log.error(f"[WEB] Error generating upload page: {e}")
            return self.generate_500()
    
    async def handle_config_upload(self, request_str):
        """Handle config file upload and validation."""
        try:
            # Parse multipart form data (simplified for MicroPython)
            lines = request_str.split('\r\n')
            
            # Find the boundary
            boundary = None
            for line in lines:
                if line.startswith('Content-Type: multipart/form-data'):
                    boundary_part = line.split('boundary=')
                    if len(boundary_part) > 1:
                        boundary = '--' + boundary_part[1]
                        break
            
            if not boundary:
                return self.generate_upload_error("Invalid multipart data")
            
            # Find the file content
            file_content = None
            in_file_data = False
            content_lines = []
            
            for line in lines:
                if in_file_data:
                    if line.startswith(boundary):
                        break
                    content_lines.append(line)
                elif 'Content-Disposition: form-data' in line and 'filename=' in line:
                    # Skip the next line (Content-Type) and empty line
                    in_file_data = True
                    continue
            
            if content_lines:
                file_content = '\r\n'.join(content_lines).strip()
            
            if not file_content:
                return self.generate_upload_error("No file content found")
            
            # Validate JSON
            try:
                config_data = json.loads(file_content)
            except json.JSONDecodeError as e:
                return self.generate_upload_error(f"Invalid JSON format: {e}")
            
            # Backup current config
            try:
                os.rename('config.json', 'config.json.backup')
            except:
                pass  # Backup failed, continue anyway
            
            # Save new config
            try:
                with open('config.json', 'w') as f:
                    f.write(file_content)
                
                # Validate the new config using config manager
                config.config_manager.reload()
                
                # If we get here, config is valid
                log.info("[WEB] New configuration uploaded and validated successfully")
                
                # Generate success response with auto-reboot
                html = """<!DOCTYPE html>
<html>
<head>
    <title>Upload Success - PagodaLightPico</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="5;url=/">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; text-align: center; }
        .success { background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 4px; margin: 20px 0; color: #155724; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Configuration Updated Successfully</h1>
        <div class="success">
            <p>The new configuration has been uploaded and validated. The system will perform a soft reboot in a few seconds.</p>
            <p>You will be redirected to the home page automatically.</p>
        </div>
        <p><a href="/">Return to Home</a></p>
    </div>
</body>
</html>"""
                
                # Schedule soft reboot after response is sent
                asyncio.create_task(self.soft_reboot_delayed())
                
                response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(html)}\r\nConnection: close\r\n\r\n{html}"
                return response
                
            except Exception as e:
                # Restore backup if validation failed
                try:
                    os.rename('config.json.backup', 'config.json')
                except:
                    pass
                return self.generate_upload_error(f"Configuration validation failed: {e}")
                
        except Exception as e:
            log.error(f"[WEB] Error handling config upload: {e}")
            return self.generate_upload_error(f"Upload processing failed: {e}")
    
    def generate_upload_error(self, error_msg):
        """Generate upload error page."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Upload Error - PagodaLightPico</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        .error {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 4px; margin: 20px 0; color: #721c24; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Upload Failed</h1>
        <div class="error">
            <p><strong>Error:</strong> {error_msg}</p>
        </div>
        <p><a href="/upload-config">Try Again</a> | <a href="/">Back to Home</a></p>
    </div>
</body>
</html>"""
        
        response = f"HTTP/1.1 400 Bad Request\r\nContent-Type: text/html\r\nContent-Length: {len(html)}\r\nConnection: close\r\n\r\n{html}"
        return response
    
    async def soft_reboot_delayed(self):
        """Perform soft reboot after a short delay."""
        try:
            await asyncio.sleep(3)  # Wait 3 seconds
            log.info("[WEB] Performing soft reboot after config update")
            machine.soft_reset()
        except Exception as e:
            log.error(f"[WEB] Error during soft reboot: {e}")

# Global web server instance
web_server = AsyncWebServer()