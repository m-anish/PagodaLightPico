"""
Network diagnostics module for PagodaLightPico.

Provides utilities to diagnose and monitor network-related issues
including timeouts, connection stability, and performance metrics.
"""

import time
import gc
from simple_logger import Logger

log = Logger()

class NetworkDiagnostics:
    """Network diagnostics and monitoring utilities."""
    
    def __init__(self):
        self.connection_stats = {
            'wifi_disconnects': 0,
            'mqtt_disconnects': 0,
            'web_timeouts': 0,
            'last_wifi_check': 0,
            'last_mqtt_check': 0,
            'memory_warnings': 0
        }
    
    def check_wifi_stability(self):
        """Check WiFi connection stability."""
        try:
            import network
            wlan = network.WLAN(network.STA_IF)
            
            if not wlan.isconnected():
                self.connection_stats['wifi_disconnects'] += 1
                log.error(f"[DIAG] WiFi disconnected (total: {self.connection_stats['wifi_disconnects']})")
                return False
            
            # Check signal strength if available
            try:
                rssi = wlan.status('rssi')
                if rssi < -70:  # Weak signal
                    log.warn(f"[DIAG] Weak WiFi signal: {rssi} dBm")
            except:
                pass
            
            self.connection_stats['last_wifi_check'] = time.time()
            return True
            
        except Exception as e:
            log.error(f"[DIAG] WiFi check error: {e}")
            return False
    
    def check_mqtt_health(self, mqtt_notifier):
        """Check MQTT connection health."""
        try:
            if mqtt_notifier.notifications_enabled and not mqtt_notifier.connected:
                self.connection_stats['mqtt_disconnects'] += 1
                log.error(f"[DIAG] MQTT disconnected (total: {self.connection_stats['mqtt_disconnects']})")
                return False
            
            self.connection_stats['last_mqtt_check'] = time.time()
            return True
            
        except Exception as e:
            log.error(f"[DIAG] MQTT check error: {e}")
            return False
    
    def check_memory_health(self, threshold=10000):
        """Check memory usage and warn if low."""
        try:
            gc.collect()
            free_memory = gc.mem_free()
            
            if free_memory < threshold:
                self.connection_stats['memory_warnings'] += 1
                log.warn(f"[DIAG] Low memory: {free_memory} bytes (warnings: {self.connection_stats['memory_warnings']})")
                return False
            
            return True
            
        except Exception as e:
            log.error(f"[DIAG] Memory check error: {e}")
            return False
    
    def record_web_timeout(self):
        """Record a web server timeout event."""
        self.connection_stats['web_timeouts'] += 1
        log.error(f"[DIAG] Web timeout recorded (total: {self.connection_stats['web_timeouts']})")
    
    def get_diagnostics_summary(self):
        """Get a summary of network diagnostics."""
        return {
            'uptime': time.time(),
            'stats': self.connection_stats.copy(),
            'memory_free': gc.mem_free() if 'gc' in globals() else 'unknown'
        }
    
    def log_diagnostics_summary(self):
        """Log a summary of network diagnostics."""
        summary = self.get_diagnostics_summary()
        log.info(f"[DIAG] Network Summary:")
        log.info(f"[DIAG]   WiFi disconnects: {summary['stats']['wifi_disconnects']}")
        log.info(f"[DIAG]   MQTT disconnects: {summary['stats']['mqtt_disconnects']}")
        log.info(f"[DIAG]   Web timeouts: {summary['stats']['web_timeouts']}")
        log.info(f"[DIAG]   Memory warnings: {summary['stats']['memory_warnings']}")
        log.info(f"[DIAG]   Free memory: {summary['memory_free']} bytes")

# Global diagnostics instance
network_diagnostics = NetworkDiagnostics()