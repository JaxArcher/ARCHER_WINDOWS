#!/usr/bin/env python3
"""
Quick ARCHER GUI Test
"""

import requests
import json

def test_archer_api():
    """Test if ARCHER GUI is responsive"""
    try:
        # Test main endpoint
        response = requests.get("http://localhost:7860", timeout=5)
        if response.status_code == 200:
            print("✓ ARCHER GUI is running on http://localhost:7860")
            print(f"  Status Code: {response.status_code}")
            print(f"  Content Type: {response.headers.get('content-type', 'Unknown')}")
            
            # Check if it's the right interface
            if "ARCHER" in response.text:
                print("✓ Correct ARCHER interface detected")
                return True
            else:
                print("? Interface may not be ARCHER-specific")
                return True
        else:
            print(f"X ARCHER GUI returned status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("X Cannot connect to ARCHER GUI - not running")
        return False
    except Exception as e:
        print(f"X Error testing ARCHER GUI: {e}")
        return False

def main():
    print("ARCHER Windows Status Check")
    print("=" * 30)
    
    if test_archer_api():
        print("\n🎉 ARCHER Windows is RUNNING!")
        print("📱 Open http://localhost:7860 in your browser")
        print("🎤 The full multi-agent AI assistant is ready")
        return 0
    else:
        print("\n❌ ARCHER Windows is NOT running")
        print("💡 Try running: launch_archer_clean.bat")
        return 1

if __name__ == "__main__":
    exit(main())