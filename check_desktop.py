#!/usr/bin/env python3
"""
ARCHER Desktop Status Check
"""

import time
import psutil

def check_gui_running():
    """Check if ARCHER desktop GUI is running"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'python' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'simple_desktop_gui.py' in cmdline:
                        print(f"+ ARCHER Desktop GUI is running (PID: {proc.info['pid']})")
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        print("- ARCHER Desktop GUI not found in running processes")
        return False
        
    except Exception as e:
        print(f"X Error checking GUI status: {e}")
        return False

def main():
    print("ARCHER Desktop GUI Status Check")
    print("=" * 40)
    
    if check_gui_running():
        print("\nARCHER Desktop Interface:")
        print("+ Type your commands in the desktop window")
        print("+ Use the input field to interact with ARCHER")
        print("+ Full multi-agent system available through desktop")
        print("\nFeatures Available:")
        print("+ Voice synthesis (TTS)")
        print("+ Multi-agent architecture") 
        print("+ 4-tier memory system")
        print("+ Specialized agents (Assistant, Therapist, Trainer, etc.)")
    else:
        print("\nTo launch ARCHER Desktop GUI:")
        print("  python simple_desktop_gui.py")
        print("\nOr use the launcher:")
        print("  launch_archer_desktop.bat")

if __name__ == "__main__":
    main()