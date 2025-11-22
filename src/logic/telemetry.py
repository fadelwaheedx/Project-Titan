import threading
import time
import paramiko
import re

class TrafficPoller:
    def __init__(self, ip, user, password):
        self.ip = ip
        self.user = user
        self.password = password
        self.running = False
        self.current_interface = "ether1" # Default
        self._lock = threading.Lock()
        self.stats = {"rx": 0, "tx": 0}
        self._thread = None
        self._client = None # Persistent SSH client

    def set_interface(self, interface):
        with self._lock:
            self.current_interface = interface

    def get_stats(self):
        with self._lock:
            return self.stats

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._client:
            try:
                self._client.close()
            except:
                pass
        if self._thread:
            self._thread.join(timeout=1)

    def _poll_loop(self):
        # Initial connection attempt
        self._connect()
        
        while self.running:
            try:
                if not self._client or not self._client.get_transport() or not self._client.get_transport().is_active():
                    print("SSH disconnected. Reconnecting...")
                    self._connect()
                
                if self._client:
                    self._fetch_data()
            except Exception as e:
                print(f"Polling Error: {e}")
            
            time.sleep(1)

    def _connect(self):
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(self.ip, username=self.user, password=self.password, timeout=5)
        except Exception as e:
            print(f"Connection Error: {e}")
            self._client = None

    def _fetch_data(self):
        try:
            with self._lock:
                iface = self.current_interface

            # Use 'once' which works fine over exec_command even with persistent connection
            cmd = f"/interface monitor-traffic interface={iface} once"
            stdin, stdout, stderr = self._client.exec_command(cmd)
            output = stdout.read().decode().strip()
            
            rx = 0
            tx = 0
            
            # Regex to find values. Handles kbps, Mbps, bps.
            rx_match = re.search(r"rx-bits-per-second:\s*([\d\.]+)([kMGT]?bps)?", output)
            tx_match = re.search(r"tx-bits-per-second:\s*([\d\.]+)([kMGT]?bps)?", output)
            
            if rx_match:
                val = float(rx_match.group(1))
                unit = rx_match.group(2) or "bps"
                rx = self._convert_to_bps(val, unit)
                
            if tx_match:
                val = float(tx_match.group(1))
                unit = tx_match.group(2) or "bps"
                tx = self._convert_to_bps(val, unit)
            
            with self._lock:
                self.stats = {"rx": rx, "tx": tx}
                
        except Exception as e:
            print(f"SSH Poll Exception: {e}")
            # Force reconnection on next loop
            if self._client:
                self._client.close()
                self._client = None

    def _convert_to_bps(self, value, unit):
        unit = unit.lower()
        if "k" in unit:
            return value * 1000
        elif "m" in unit:
            return value * 1000000
        elif "g" in unit:
            return value * 1000000000
        return value
