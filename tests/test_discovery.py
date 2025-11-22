import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import struct

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Need to import Scapy classes to match what's used in the scanner
try:
    from scapy.all import UDP, IP
except ImportError:
    # Fallback/Mock if Scapy not present (though it should be)
    UDP = "UDP"
    IP = "IP"

from discovery.mndp_scanner import MNDP_Scanner

class TestDiscovery(unittest.TestCase):
    @patch('discovery.mndp_scanner.sniff')
    def test_scanner_start_stop(self, mock_sniff):
        scanner = MNDP_Scanner()
        scanner.start_scan()
        self.assertTrue(scanner.running)
        scanner.stop_scan()
        self.assertFalse(scanner.running)

    def test_process_packet(self):
        scanner = MNDP_Scanner()
        scanner.running = True

        # Create MNDP Payload
        # Header (4 bytes 0s)
        payload = b'\x00\x00\x00\x00'

        # TLV 1: MAC Address
        # Type 1, Len 6, Value: 00:11:22:33:44:55
        mac_val = b'\x00\x11\x22\x33\x44\x55'
        payload += struct.pack("!HH", 1, 6) + mac_val

        # TLV 5: Identity
        # Type 5, Value: "TestRouter"
        ident_val = b"TestRouter"
        payload += struct.pack("!HH", 5, len(ident_val)) + ident_val

        # TLV 7: Version
        ver_val = b"7.15.3"
        payload += struct.pack("!HH", 7, len(ver_val)) + ver_val

        # Mock Packet
        mock_pkt = MagicMock()

        udp_layer = MagicMock()
        udp_layer.dport = 5678
        udp_layer.payload = payload

        ip_layer = MagicMock()
        ip_layer.src = "192.168.88.1"

        def getitem(cls):
            if cls == UDP:
                return udp_layer
            if cls == IP:
                return ip_layer
            return None

        def contains(cls):
            if cls == UDP:
                return True
            if cls == IP:
                return True
            return False

        mock_pkt.__getitem__ = MagicMock(side_effect=getitem)
        mock_pkt.__contains__ = MagicMock(side_effect=contains)

        # Run process
        scanner._process_packet(mock_pkt)

        neighbors = scanner.get_neighbors()
        self.assertEqual(len(neighbors), 1)
        n = neighbors[0]
        self.assertEqual(n['mac'], "00:11:22:33:44:55")
        self.assertEqual(n['identity'], "TestRouter")
        self.assertEqual(n['version'], "7.15.3")
        self.assertEqual(n['ip'], "192.168.88.1")

if __name__ == "__main__":
    unittest.main()
