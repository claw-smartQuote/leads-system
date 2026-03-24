---
name: wifi-control
description: Control WiFi network settings on macOS. Use when the user needs to (1) Turn WiFi on or off, (2) Connect to a specific WiFi network, (3) List available WiFi networks, (4) Show current WiFi status and connection details, (5) Toggle WiFi for troubleshooting, or (6) Get WiFi network information like IP address and signal strength.
metadata:
  {
    "openclaw":
      {
        "emoji": "📡",
        "requires": { "os": ["darwin"], "bins": ["networksetup"] },
      },
  }
---

# WiFi Control (macOS)

Control WiFi settings and connections on macOS.

**Note: This skill only works on macOS.**

## Quick Start

### Check WiFi status

```bash
python3 {baseDir}/scripts/wifi_control.py status
```

### Turn WiFi on/off

```bash
python3 {baseDir}/scripts/wifi_control.py on
python3 {baseDir}/scripts/wifi_control.py off
```

### Toggle WiFi

```bash
python3 {baseDir}/scripts/wifi_control.py toggle
```

### List available networks

```bash
python3 {baseDir}/scripts/wifi_control.py list
```

### Connect to a network

```bash
python3 {baseDir}/scripts/wifi_control.py connect "YourNetworkName"
```

### Connect with password

```bash
python3 {baseDir}/scripts/wifi_control.py connect "YourNetworkName" --password "yourpassword"
```

## Commands

| Command | Description |
|---------|-------------|
| `status` | Show current WiFi status and connection info |
| `on` | Turn WiFi on |
| `off` | Turn WiFi off |
| `toggle` | Toggle WiFi on/off |
| `list` | List available WiFi networks |
| `connect <ssid>` | Connect to a WiFi network |
| `disconnect` | Disconnect from current network |

## Features

- **Power control**: Turn WiFi on/off or toggle
- **Network listing**: See available networks with signal strength
- **Quick connect**: Connect to known networks
- **New networks**: Connect with password prompt
- **Status info**: Current network, IP address, signal strength

## Security Notes

- Passwords can be provided via `--password` flag or entered interactively
- For security, prefer interactive password entry
- Saved network passwords are stored in macOS Keychain