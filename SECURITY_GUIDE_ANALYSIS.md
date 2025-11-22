# MikroTik Security Guide Analysis (Top 10)

Based on the "MikroTik Security Guide, Second Edition", the following top 10 mandatory security configurations were extracted for a network administrator to implement on a new RouterOS device.

## Top 10 Critical Security Configurations

| Priority | Category | Description / Rationale | Specific RouterOS CLI Command |
| :--- | :--- | :--- | :--- |
| **1** | **Credentials** | **Secure Admin Account:** Create a new full-access user and disable the default 'admin' account to prevent dictionary attacks. | `/user add name=myAdmin group=full password="StrongPass123!" comment="Owner"; /user disable admin` |
| **2** | **Hardening** | **Disable Insecure Services:** Turn off unused and unencrypted services (Telnet, FTP, WWW, API) to minimize the attack surface. | `/ip service disable telnet,ftp,www,api,api-ssl` |
| **3** | **Access Control** | **Restrict Management IP:** Whitelist trusted administrative subnets for Winbox and SSH access. | `/ip service set winbox,ssh address=192.168.88.0/24` |
| **4** | **L2 Visibility** | **Disable Neighbor Discovery:** Prevent the router from broadcasting its identity and version to the local network (MNDP/CDP). | `/ip neighbor discovery-settings set discover-interface-list=none; /tool mac-server set allowed-interface-list=none` |
| **5** | **IP Services** | **Disable Open DNS:** Prevent the router from acting as an Open DNS Resolver, which can be used in DDoS amplification attacks. | `/ip dns set allow-remote-requests=no` |
| **6** | **SSH Security** | **Enforce Strong Crypto:** Disable weak ciphers and enforce strong cryptography for SSH connections. | `/ip ssh set strong-crypto=yes` |
| **7** | **Anti-Spoofing** | **Reverse Path Filtering:** Enable Strict RPF to drop packets where the source IP does not match the routing table (spoofing protection). | `/ip settings set rp-filter=strict` |
| **8** | **Firewall (Input)** | **Drop Invalid:** Discard packets with an 'invalid' connection state (malformed or out-of-sequence) immediately. | `/ip firewall filter add chain=input connection-state=invalid action=drop comment="Drop Invalid" place-before=0` |
| **9** | **Firewall (Input)** | **Accept Established/Related:** Allow return traffic for connections originated by the router or permitted new connections. | `/ip firewall filter add chain=input connection-state=established,related action=accept comment="Accept Est/Rel"` |
| **10** | **Firewall (Input)** | **Default Deny (WAN):** Explicitly drop all other traffic coming from the WAN interface to protect the device control plane. | `/ip firewall filter add chain=input in-interface-list=WAN action=drop comment="Drop All WAN Input"` |

## Administrator Notes
*   **Interface Lists:** Command #10 assumes you have an Interface List named `WAN` configured.
*   **Order Matters:** Firewall rules are processed sequentially.
*   **Subnets:** Replace `192.168.88.0/24` with your actual management subnet.
