#!/usr/bin/env python3
"""
WiFi Control Tool for macOS
Control WiFi settings using networksetup and airport utilities
"""

import argparse
import sys
import subprocess
import re
import platform


def check_macos():
    """Check if running on macOS"""
    if platform.system() != "Darwin":
        print("Error: This tool only works on macOS")
        sys.exit(1)


def run_command(cmd, capture=True):
    """Run a shell command"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def get_wifi_interface():
    """Get the WiFi interface name (usually en0)"""
    success, stdout, stderr = run_command("networksetup -listallhardwareports")
    
    if not success:
        return None
    
    # Parse output to find WiFi interface
    lines = stdout.split('\n')
    for i, line in enumerate(lines):
        if 'Wi-Fi' in line or 'AirPort' in line:
            # Look for Device: line after this
            for j in range(i+1, min(i+5, len(lines))):
                if 'Device:' in lines[j]:
                    match = re.search(r'Device:\s*(\w+)', lines[j])
                    if match:
                        return match.group(1)
    
    # Default to en0 if not found
    return "en0"


def get_wifi_status():
    """Get current WiFi status"""
    interface = get_wifi_interface()
    
    # Check power status
    success, stdout, stderr = run_command(f"networksetup -getairportpower {interface}")
    power_status = "Unknown"
    if success:
        if "On" in stdout:
            power_status = "On"
        elif "Off" in stdout:
            power_status = "Off"
    
    # Get current network info
    success, stdout, stderr = run_command("networksetup -getairportnetwork " + interface)
    current_network = "Not connected"
    if success and "Current Wi-Fi Network:" in stdout:
        match = re.search(r'Current Wi-Fi Network:\s*(.+)', stdout)
        if match:
            current_network = match.group(1).strip()
    
    # Get IP address
    success, stdout, stderr = run_command(f"ipconfig getifaddr {interface}")
    ip_address = stdout.strip() if success else "N/A"
    
    return {
        'power': power_status,
        'network': current_network,
        'interface': interface,
        'ip': ip_address
    }


def set_wifi_power(on=True):
    """Turn WiFi on or off"""
    interface = get_wifi_interface()
    status = "on" if on else "off"
    
    success, stdout, stderr = run_command(
        f"networksetup -setairportpower {interface} {status}"
    )
    
    if success:
        print(f"WiFi turned {status}")
        return True
    else:
        print(f"Failed to turn WiFi {status}: {stderr}")
        return False


def toggle_wifi():
    """Toggle WiFi on/off"""
    status = get_wifi_status()
    if status['power'] == "On":
        return set_wifi_power(False)
    else:
        return set_wifi_power(True)


def list_networks():
    """List available WiFi networks"""
    interface = get_wifi_interface()
    
    print("Scanning for WiFi networks...")
    success, stdout, stderr = run_command(
        f"/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport {interface} -s"
    )
    
    if not success:
        # Try alternative method
        success, stdout, stderr = run_command(
            f"networksetup -listpreferredwirelessnetworks {interface}"
        )
        if success:
            print("\nPreferred Networks:")
            print(stdout)
        else:
            print(f"Failed to list networks: {stderr}")
        return
    
    # Parse airport scan output
    lines = stdout.strip().split('\n')
    if len(lines) <= 1:
        print("No networks found")
        return
    
    print("\nAvailable Networks:")
    print(f"{'SSID':<30} {'Security':<15}")
    print("-" * 50)
    
    for line in lines[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 2:
            # First part is usually SSID (may contain spaces, tricky to parse)
            # For simplicity, show raw line
            print(line)


def connect_to_network(ssid, password=None):
    """Connect to a WiFi network"""
    interface = get_wifi_interface()
    
    print(f"Connecting to '{ssid}'...")
    
    if password:
        cmd = f'networksetup -setairportnetwork {interface} "{ssid}" "{password}"'
    else:
        cmd = f'networksetup -setairportnetwork {interface} "{ssid}"'
    
    success, stdout, stderr = run_command(cmd)
    
    if success:
        print(f"✅ Connected to '{ssid}'")
        # Show new status
        print("\nConnection details:")
        show_status()
        return True
    else:
        print(f"❌ Failed to connect: {stderr}")
        return False


def disconnect():
    """Disconnect from current network"""
    interface = get_wifi_interface()
    
    success, stdout, stderr = run_command(
        f"networksetup -setairportnetwork {interface} \"\""
    )
    
    if success:
        print("Disconnected from WiFi network")
        return True
    else:
        print(f"Failed to disconnect: {stderr}")
        return False


def show_status():
    """Display WiFi status"""
    status = get_wifi_status()
    
    print(f"\n📡 WiFi Status")
    print(f"   Interface: {status['interface']}")
    print(f"   Power: {'🟢 On' if status['power'] == 'On' else '🔴 Off'}")
    print(f"   Network: {status['network']}")
    print(f"   IP Address: {status['ip']}")


def main():
    check_macos()
    
    parser = argparse.ArgumentParser(description='Control WiFi on macOS')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Status command
    subparsers.add_parser('status', help='Show WiFi status')
    
    # On command
    subparsers.add_parser('on', help='Turn WiFi on')
    
    # Off command
    subparsers.add_parser('off', help='Turn WiFi off')
    
    # Toggle command
    subparsers.add_parser('toggle', help='Toggle WiFi on/off')
    
    # List command
    subparsers.add_parser('list', help='List available networks')
    
    # Connect command
    connect_parser = subparsers.add_parser('connect', help='Connect to a network')
    connect_parser.add_argument('ssid', help='Network name (SSID)')
    connect_parser.add_argument('--password', '-p', help='Network password')
    
    # Disconnect command
    subparsers.add_parser('disconnect', help='Disconnect from current network')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'status':
        show_status()
    elif args.command == 'on':
        set_wifi_power(True)
    elif args.command == 'off':
        set_wifi_power(False)
    elif args.command == 'toggle':
        toggle_wifi()
    elif args.command == 'list':
        list_networks()
    elif args.command == 'connect':
        # Prompt for password if not provided
        password = args.password
        if not password:
            import getpass
            password = getpass.getpass(f"Password for '{args.ssid}' (press Enter if none): ")
            if password == "":
                password = None
        connect_to_network(args.ssid, password)
    elif args.command == 'disconnect':
        disconnect()


if __name__ == '__main__':
    main()