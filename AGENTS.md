# Project Titan - Architecture & Agent Guidelines

This document provides technical context for AI agents working on Project Titan.

## Architecture Overview

*   **Frontend:** **Flet** (Python wrapper for Flutter). Provides the GUI logic.
*   **Visualization:** **Cytoscape.js** embedded in a Flet `WebView`.
    *   **Bridge:** Python serves the HTML via a local background `http.server` thread.
    *   **Communication:** Python injects data via `webview.evaluate_javascript()`. JavaScript sends events via `window.chrome.webview.postMessage()` (or platform equivalents).
*   **Connectivity:**
    *   **SSH/SFTP:** `Paramiko` for management and file transfer.
    *   **Discovery:** `Scapy` for sniffing MNDP packets on UDP port 5678.

## Core Mechanics

### 1. The "Script Injection" Strategy (Deployment)
To prevent connection drops during network reconfiguration (IP/VLAN changes) from killing the deployment process, we **never** run commands line-by-line via API.

**Workflow:**
1.  **Generate:** Create a monolithic `setup.rsc` file locally.
2.  **Upload:** SFTP the file to the router (detecting `/flash` directory if present).
3.  **Schedule:** Create a RouterOS Scheduler task (`TITAN_DEPLOY`) to execute the script locally.
    *   *Command:* `/import file=flash/setup.rsc verbose=yes`
    *   *Trigger:* Offset start time (e.g., `current time + 2s`).
4.  **Disconnect:** Close SSH immediately.
5.  **Poll:** Ping the target IP until the router returns.

### 2. "Panic Wipe" (Dead Man's Switch)
Before applying firewall rules, a `safe_mode_rollback.rsc` is uploaded and scheduled to run in 10 minutes. If the application successfully reconnects after deployment, this schedule is removed. If not, the router resets, preventing permanent lockouts.

## Build System
The project uses `PyInstaller` managed by `tools/build.py`.
*   **Assets:** The `assets/` folder is bundled using `--add-data`.
*   **Runtime:** The application detects if it is running frozen (`sys.frozen`) and resolves asset paths using `sys._MEIPASS`.
*   **Hidden Imports:** `scapy.layers.all` must be explicitly included.
