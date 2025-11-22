# Project Titan: Conflict Zone / Survival Mode Analysis

## 1. Executive Summary
Standard security frameworks (NIST, CIS) prioritize Confidentiality, Integrity, and Availability (CIA). In a kinetic conflict zone (Gaza scenario), the hierarchy of needs shifts. "Availability" becomes the only priority, but it is threatened by physical factors (power, shrapnel) rather than cyber threats.

This analysis defines the "Survival Profile" for RouterOS devices. This profile is not designed to pass a PCI-DSS audit; it is designed to keep the link alive on 10% battery while under indirect fire.

## 2. The Shift in Threat Modeling

| Feature | Standard Enterprise Model | Conflict Zone / Survival Model |
| :--- | :--- | :--- |
| **Primary Threat** | Ransomware, Data Exfiltration, DDoS | Power Failure, Kinetic Damage, Hardware Scarcity |
| **Power Source** | Grid + Backup Generator + UPS | Car Battery (12V), Sporadic Solar, Unstable Grid |
| **Connectivity** | Redundant Fiber/ISP | Daisy-chained Wireless, Scavenged Microwave Links |
| **Hardware** | Replaceable (Next Day Delivery) | Irreplaceable (Zero Supply Chain) |
| **Admin Access** | VPN / Zero Trust | Local Cable (Console/Ether) Only |

## 3. Technical Requirements for "Profile: SCARCITY"

### 3.1 Power Conservation (The "Calorie Deficit" Protocol)
*   **Objective:** Reduce wattage draw to absolute minimum to extend battery life.
*   **Action:**
    *   Disable all unused interfaces immediately.
    *   Downclock CPU if load permits (RouterOS v7 hardware dependent).
    *   Disable LCD screens, LEDs (stealth + power), and Beeper.
    *   Disable heavy packages (iot, gps, ups unless critical).

### 3.2 Resilience & Automation (The "Ghost" Protocol)
*   **Objective:** Self-healing. Physical access to the device may be impossible due to danger.
*   **Action:**
    *   **Watchdog:** Aggressive ping checks. If gateway is lost, cycle the interface (don't just wait).
    *   **Safe Mode Discipline:** Enforce "Safe Mode" logic in all change scripts.
    *   **Reboot Schedule:** Scheduled reboots to clear memory leaks are risky if the device doesn't come back. Disable auto-reboots.

### 3.3 Security as Resource Management
*   **Objective:** Reduce CPU load caused by processing malicious traffic.
*   **Action:**
    *   **Raw Table:** Drop bad traffic in Prerouting (RAW table) to bypass Connection Tracking (which eats RAM/CPU).
    *   **Services:** Disable all discovery protocols (MNDP, CDP, LLDP). Silence is safety.

## 4. The "Five Stages" Implementation Plan
The configuration template (`routeros_survival.rsc`) implements the "Acceptance" stage: accepting that the environment is hostile and the hardware is dying.

*   **Denial:** (Skipped)
*   **Anger:** (Skipped)
*   **Bargaining:** (Skipped)
*   **Depression:** (Skipped)
*   **Acceptance:** Automation of survival tasks.

**Author:** Jules / System Architect
**Status:** APPROVED for Conflict Zone Deployment
