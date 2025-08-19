"""
Test script for mDNS service functionality.

This script can be used to test the mDNS service independently
of the main application.
"""

import network
import time
from lib.mdns_service import MDNSService
from simple_logger import Logger

# Set up logging
log = Logger()
log.info("Starting mDNS test script")

def test_mdns():
    """Test mDNS service functionality."""
    
    # Check WiFi connection
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        log.error("WiFi not connected - mDNS test requires network connection")
        return False
    
    ip_address = wlan.ifconfig()[0]
    log.info(f"WiFi connected with IP: {ip_address}")
    
    # Create test mDNS service
    test_service = MDNSService(hostname="test-lighthouse", service_name="Test PagodaLight")
    
    try:
        # Start mDNS service
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
                    test_service.update_service_info(test_status="running", uptime=str(i))
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
