import threading
import struct
import socket
import time
from scapy.all import sniff, UDP, IP, Ether
from scapy.config import conf

class MNDP_Scanner:
    """
    Scanner for MikroTik Neighbor Discovery Protocol (MNDP).
    Listens on UDP/5678 using Scapy.
    Parses TLV (Type-Length-Value) fields to extract device info.
    """
    
    MNDP_PORT = 5678
    MNDP_IP = "255.255.255.255" # Broadcast
    
    # TLV Type Constants
    TLV_MAC_ADDRESS = 1
    TLV_IDENTITY = 5
    TLV_VERSION = 7
    TLV_PLATFORM = 8
    TLV_UPTIME = 10
    TLV_INTERFACE_NAME = 16

    def __init__(self):
        self.neighbors = {} # Keyed by MAC to avoid duplicates
        self.running = False
        self._lock = threading.Lock()
        self._sniff_thread = None

    def start_scan(self):
        """Starts the scanning process in a background thread."""
        if self.running:
            return
            
        self.running = True
        self.neighbors = {} # Clear previous results
        
        # Start sniffing in a separate thread
        self._sniff_thread = threading.Thread(target=self._sniff_packet, daemon=True)
        self._sniff_thread.start()
        print("MNDP Scapy Scanner Started...")

    def stop_scan(self):
        """Stops the scanning process."""
        self.running = False

    def _sniff_packet(self):
        """Scapy sniff loop."""
        # filter: UDP port 5678
        # stop_filter: check self.running
        try:
            sniff(filter=f"udp port {self.MNDP_PORT}", 
                  prn=self._process_packet, 
                  store=0, 
                  stop_filter=lambda x: not self.running)
        except Exception as e:
            print(f"Scapy Sniff Error: {e}")
            self.running = False

    def _process_packet(self, packet):
        """
        Callback for each captured packet.
        Parses MNDP payload if present.
        """
        if not self.running:
            return

        if UDP in packet and packet[UDP].dport == self.MNDP_PORT:
            try:
                payload = bytes(packet[UDP].payload)
                info = self._parse_mndp_payload(payload)
                
                # Add IP from the packet header if available
                if IP in packet:
                    info['ip'] = packet[IP].src
                else:
                    # Fallback for non-IP frames (rare for UDP transport but good practice)
                    info['ip'] = "0.0.0.0"

                # Use MAC as unique key
                if 'mac' in info:
                    with self._lock:
                        # Update or add neighbor
                        self.neighbors[info['mac']] = info
            except Exception as e:
                print(f"Error parsing packet: {e}")

    def _parse_mndp_payload(self, payload):
        """
        Parses the raw bytes of the MNDP payload (TLV format).
        Structure: Type (2 bytes), Length (2 bytes), Value (Variable)
        """
        offset = 4 # Skip initial 4 bytes (Header/Seq?) - usually 00 00 00 00 or specific header
                   # MNDP usually starts with header.
        
        info = {}
        
        while offset + 4 <= len(payload):
            # Big Endian Unpacking
            tlv_type, tlv_len = struct.unpack("!HH", payload[offset:offset+4])
            offset += 4
            
            if offset + tlv_len > len(payload):
                break # Malformed or truncated
            
            value_bytes = payload[offset:offset+tlv_len]
            offset += tlv_len
            
            if tlv_type == self.TLV_MAC_ADDRESS:
                # Standard MAC format
                info['mac'] = ':'.join(f'{b:02x}' for b in value_bytes)
            
            elif tlv_type == self.TLV_IDENTITY:
                info['identity'] = value_bytes.decode('utf-8', errors='ignore')
                
            elif tlv_type == self.TLV_VERSION:
                info['version'] = value_bytes.decode('utf-8', errors='ignore')
                
            elif tlv_type == self.TLV_PLATFORM:
                info['platform'] = value_bytes.decode('utf-8', errors='ignore')
                
            elif tlv_type == self.TLV_INTERFACE_NAME:
                info['interface'] = value_bytes.decode('utf-8', errors='ignore')
                
            elif tlv_type == self.TLV_UPTIME:
                # Uptime is usually 4 bytes integer (seconds)
                if len(value_bytes) == 4:
                    uptime_sec = struct.unpack("!I", value_bytes)[0]
                    info['uptime'] = uptime_sec

        return info

    def get_neighbors(self):
        """
        Returns the list of discovered neighbors.
        """
        with self._lock:
            return list(self.neighbors.values())

    def get_neighbors_json(self):
        """
        Returns neighbors formatted for Cytoscape.js (Node List).
        """
        import json
        nodes = []
        edges = []
        
        # Central node (The PC running the app)
        nodes.append({"data": {"id": "PC", "label": "Titan Commander", "color": "#555"}})
        
        with self._lock:
            for neighbor in self.neighbors.values():
                mac = neighbor.get('mac', 'Unknown')
                identity = neighbor.get('identity', mac)
                version = neighbor.get('version', '?')
                ip = neighbor.get('ip', '0.0.0.0')
                
                # Color logic based on version
                color = "#ff8c00" # Orange (v6/Legacy default)
                if "v7" in version or version.startswith("7"):
                    color = "#007acc" # Blue (v7)
                
                node_id = mac
                label = f"{identity}\n{ip}\n{version}"
                
                nodes.append({
                    "data": {
                        "id": node_id,
                        "label": label,
                        "color": color,
                        "info": neighbor # Store full info for click handler
                    }
                })
                
                # Edge from PC to Node
                edges.append({
                    "data": {
                        "source": "PC",
                        "target": node_id
                    }
                })
                
        return json.dumps(nodes + edges)

if __name__ == "__main__":
    # Test run
    scanner = MNDP_Scanner()
    scanner.start_scan()
    try:
        while True:
            time.sleep(5)
            print(scanner.get_neighbors())
    except KeyboardInterrupt:
        scanner.stop_scan()
