"""
Test script for mDNS service functionality.

This script can be used to test the mDNS service independently
of the main application. It handles its own WiFi connection using
settings from config.json.
"""

import network
import time
from lib.mdns_service import MDNSService
from lib.config_manager import ConfigManager
from simple_logger import Logger
from machine import Pin

# Set up logging
log = Logger()
log.info("Starting mDNS test script")

def connect_wifi_standalone(timeout=15):
    """
    Connect to WiFi using settings from config.json.
    
    Args:
        timeout (int): Connection timeout in seconds
        
    Returns:
        bool: True if connected successfully, False otherwise
    """
    try:
        # Load configuration
        config = ConfigManager()
        log.info(f"Loaded config - attempting to connect to WiFi: {config.WIFI_SSID}")
        
        # Initialize WiFi
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        
        # Check if already connected
        if wlan.isconnected():
            ip_address = wlan.ifconfig()[0]
            log.info(f"WiFi already connected with IP: {ip_address}")
            return True
        
        # Connect to WiFi
        log.info("Connecting to WiFi...")
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        
        # Wait for connection
        start_time = time.time()
        while not wlan.isconnected():
            if time.time() - start_time > timeout:
                log.error(f"WiFi connection timed out after {timeout} seconds")
                return False
            
            # Show progress
            elapsed = int(time.time() - start_time)
            if elapsed % 2 == 0:  # Every 2 seconds
                log.info(f"  Connecting... ({elapsed}s elapsed)")
            
            time.sleep(0.5)
        
        # Connection successful
        ip_address = wlan.ifconfig()[0]
        log.info(f"✅ WiFi connected successfully with IP: {ip_address}")
        return True
        
    except Exception as e:
        log.error(f"❌ WiFi connection failed: {e}")
        return False

def show_network_info():
    """Display network information for diagnostics."""
    try:
        wlan = network.WLAN(network.STA_IF)
        if wlan.isconnected():
            ip, subnet, gateway, dns = wlan.ifconfig()
            log.info(f"📊 Network Information:")
            log.info(f"   IP Address: {ip}")
            log.info(f"   Subnet Mask: {subnet}")
            log.info(f"   Gateway: {gateway}")
            log.info(f"   DNS Server: {dns}")
            log.info(f"   Signal Strength: {wlan.status('rssi')} dBm")
        else:
            log.warn("Network not connected - cannot show network info")
    except Exception as e:
        log.error(f"Error getting network info: {e}")

def test_mdns():
    """Test mDNS service functionality."""
    
    log.info("🚀 Starting comprehensive mDNS test...")
    
    # First, connect to WiFi
    log.info("🌐 Step 1: Connecting to WiFi...")
    if not connect_wifi_standalone():
        log.error("❌ Cannot test mDNS without WiFi connection")
        return False
    
    # Show network diagnostics
    log.info("📊 Step 2: Network diagnostics...")
    show_network_info()
    
    # Get IP address for logging
    wlan = network.WLAN(network.STA_IF)
    ip_address = wlan.ifconfig()[0]
    
    log.info("🏮 Step 3: Testing mDNS service...")
    
    # Create test mDNS service
    test_service = MDNSService(hostname="test-lighthouse", service_name="Test PagodaLight")
    
    try:
        # Start mDNS service
        log.info("   Starting mDNS server...")
        if test_service.start(web_server_port=8080):
            log.info("✅ mDNS service started successfully")
            log.info(f"🔗 Test URL: {test_service.get_hostname_url()}")
            log.info("📡 Service should be discoverable as 'test-lighthouse.local'")
            
            # Run for 30 seconds
            log.info("🕐 Running test for 30 seconds...")
            for i in range(30):
                time.sleep(1)
                if i % 5 == 0:
                    log.info(f"   {30-i} seconds remaining...")
                    
                # Test service info update
                if i == 15:
                    test_service.update_service_info({"test_status": "running", "uptime": str(i)})
                    log.info("🔄 Updated service info")
            
            # Stop service
            test_service.stop()
            log.info("✅ mDNS test completed successfully")
            return True
            
        else:
            log.error("❌ Failed to start mDNS service")
            return False
            
    except Exception as e:
        log.error(f"❌ mDNS test failed: {e}")
        if test_service.running:
            test_service.stop()
        return False

if __name__ == "__main__":
    success = test_mdns()
    if success:
        log.info("🎉 mDNS test PASSED")
    else:
        log.error("💥 mDNS test FAILED")
