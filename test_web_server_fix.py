#!/usr/bin/env python3
"""
Test script to verify the web server fixes work correctly.
Specifically tests the generate_main_page method for syntax errors.
"""

import sys
import os

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

# Mock the required modules
class MockLogger:
    def info(self, msg):
        print(f"INFO: {msg}")
    
    def error(self, msg):
        print(f"ERROR: {msg}")
    
    def debug(self, msg):
        print(f"DEBUG: {msg}")

class MockSystemStatus:
    def get_status_dict(self):
        return {
            'connections': {
                'wifi': True,
                'web_server': True,
                'mqtt': False
            }
        }

class MockRTCModule:
    @staticmethod
    def get_current_time():
        # Return a fixed time for testing: (year, month, day, hour, minute, second)
        return (2025, 8, 20, 10, 30, 45)

# Replace the actual modules with mocks
import lib.web_server
lib.web_server.Logger = MockLogger
lib.web_server.system_status = MockSystemStatus()
lib.web_server.rtc_module = MockRTCModule()

# Import the web server after setting up mocks
from lib.web_server import AsyncWebServer

def test_generate_main_page():
    """Test that generate_main_page works without syntax errors."""
    print("Testing generate_main_page method...")
    
    try:
        # Create web server instance
        web_server = AsyncWebServer()
        
        # Call the generate_main_page method
        response = web_server.generate_main_page()
        
        # Check if response is generated
        if response and isinstance(response, str) and len(response) > 0:
            print("✓ generate_main_page() works without syntax errors")
            print(f"✓ Response length: {len(response)} characters")
            return True
        else:
            print("✗ generate_main_page() returned empty or invalid response")
            return False
            
    except SyntaxError as e:
        print(f"✗ SyntaxError in generate_main_page(): {e}")
        return False
    except Exception as e:
        print(f"✗ Error in generate_main_page(): {e}")
        return False

def main():
    """Run the test."""
    print("Running web server fix test...\n")
    
    if test_generate_main_page():
        print("\n✓ Test passed! The fix is working correctly.")
        return True
    else:
        print("\n✗ Test failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)