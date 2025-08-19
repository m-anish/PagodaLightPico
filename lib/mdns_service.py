"""
mDNS service module for PagodaLightPico device discovery.

Provides mDNS/Bonjour support to make the device discoverable on the local
network with a friendly hostname like 'lighthouse.local' or 'pagoda.local'.

Also advertises HTTP service for the web configuration interface.
"""

import mdns
from simple_logger import Logger
import network
from lib.config_manager import config_manager

log = Logger()

class MDNSService:
    """
    mDNS service manager for device discovery and service advertisement.
    
    Makes the device discoverable with a friendly hostname and advertises
    the web configuration service.
    """
    
    def __init__(self, hostname="lighthouse", service_name="PagodaLight"):
        """
        Initialize mDNS service.
        
        Args:
            hostname (str): The hostname for mDNS (without .local)
            service_name (str): Friendly service name for discovery
        """
        self.hostname = hostname
        self.service_name = service_name
        self.mdns_server = None
        self.running = False
        
    def start(self, web_server_port=80):
        """
        Start mDNS service and advertise device and services.
        
        Args:
            web_server_port (int): Port where web server is running
            
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            # Check if WiFi is connected
            wlan = network.WLAN(network.STA_IF)
            if not wlan.isconnected():
                log.warn("mDNS service requires WiFi connection")
                return False
            
            # Get our IP address for service advertisement
            ip_address = wlan.ifconfig()[0]
            log.debug(f"Starting mDNS service with IP: {ip_address}")
            
            # Start mDNS server with hostname
            self.mdns_server = mdns.Server(ip_address)
            self.mdns_server.start(self.hostname, "Meditation lighting controller")
            
            # Advertise HTTP service for web configuration
            self.mdns_server.advertise_service(
                service_type="_http",
                protocol="_tcp", 
                port=web_server_port,
                txt_records={
                    "path": "/",
                    "device": "PagodaLightPico",
                    "version": "1.0",
                    "features": "lighting,config,status"
                }
            )
            
            # Advertise custom pagoda service for discovery by specialized apps
            self.mdns_server.advertise_service(
                service_type="_pagoda",
                protocol="_tcp",
                port=web_server_port,
                txt_records={
                    "device": "lighthouse",
                    "type": "meditation_lighting",
                    "api": "rest"
                }
            )
            
            self.running = True
            log.info(f"mDNS service started - device discoverable as '{self.hostname}.local'")
            log.info(f"Web interface: http://{self.hostname}.local/")
            log.info(f"Direct IP access: http://{ip_address}/")
            
            return True
            
        except Exception as e:
            log.error(f"Failed to start mDNS service: {e}")
            return False
    
    def stop(self):
        """Stop mDNS service."""
        try:
            if self.mdns_server and self.running:
                self.mdns_server.stop()
                self.running = False
                log.info("mDNS service stopped")
        except Exception as e:
            log.error(f"Error stopping mDNS service: {e}")
    
    def update_service_info(self, txt_records=None):
        """
        Update service information with new TXT records.
        
        Args:
            txt_records (dict): Key-value pairs to add/update in service TXT records
        """
        if not self.running:
            log.warn("Cannot update service info - mDNS not running")
            return False
            
        if txt_records is None:
            txt_records = {}
            
        try:
            # Build complete TXT records dictionary
            base_records = {
                "path": "/",
                "device": "PagodaLightPico", 
                "version": "1.0",
                "features": "lighting,config,status"
            }
            
            # Add any additional records
            for key, value in txt_records.items():
                base_records[key] = value
            
            # Re-advertise HTTP service with updated info
            self.mdns_server.advertise_service(
                service_type="_http",
                protocol="_tcp",
                port=80,
                txt_records=base_records
            )
            log.debug("mDNS service info updated")
            return True
            
        except Exception as e:
            log.error(f"Failed to update mDNS service info: {e}")
            return False

    def get_hostname_url(self):
        """
        Get the full mDNS URL for the device.
        
        Returns:
            str: The mDNS URL (e.g., "http://lighthouse.local/")
        """
        return f"http://{self.hostname}.local/"

# Global mDNS service instance
# You can customize these names to your preference:
# - "lighthouse" -> lighthouse.local
# - "pagoda" -> pagoda.local  
# - "zen" -> zen.local
# - "sanctuary" -> sanctuary.local
mdns_service = MDNSService(hostname="lighthouse", service_name="PagodaLight Meditation Center")
