# Project Titan - MikroTik Configuration Assistant

Project Titan is a professional-grade desktop application designed to configure, audit, and monitor MikroTik RouterOS v7 devices. It employs a "Wizard-First" approach to guide users from a factory-reset state to a fully hardened enterprise configuration.

## Features

*   **Configuration Wizard:** Step-by-step guide for WAN, LAN, WiFi, and Security setup.
*   **Zero-Trust Firewall:** Automatically generates strict Input/Forward chain rules.
*   **Advanced Routing:** Support for OSPFv3 and BGP peering configuration.
*   **Container Support:** Easy deployment of containerized services like PiHole/AdGuard directly on the router.
*   **Live Monitoring:** Real-time traffic dashboard for WAN/LAN interfaces.
*   **Topology Visualization:** Interactive network graph using Cytoscape.js.
*   **Security Auditor:** Automated "Gold Standard" compliance checks (Admin user, Telnet, DNS recursion).
*   **Panic Wipe:** "Dead Man's Switch" safety mechanism to prevent lockouts during configuration.

## Installation

### Prerequisites

1.  **Python 3.11+**
2.  **Npcap (Windows Only):**
    *   Download and install [Npcap](https://npcap.com/).
    *   **Crucial:** Ensure "Install in API-compatible Mode" is checked during installation. This is required for Scapy to perform MNDP discovery.

### Setup

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To start the application:

```bash
python src/main.py
```

1.  **Scan:** Use the "Scan" tab to find MikroTik devices via MNDP (UDP 5678).
2.  **Wizard:** Select a device or enter details manually to start the configuration wizard.
3.  **Deploy:** Apply the configuration using the safe "Script Injection" method.
4.  **Monitor:** View live traffic statistics.

## Building for Production

To compile the application into a standalone executable:

```bash
python tools/build.py
```

The executable will be generated in the `dist/` directory.
