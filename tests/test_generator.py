import sys
import os
import unittest

sys.path.append(os.path.join(os.getcwd(), "src"))

from logic.generator import ConfigGenerator

class TestGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = ConfigGenerator()
        self.base_ctx = {
            "lan_ip": "192.168.88.1",
            "role": "Home",
            "wan_type": "dhcp",
            "wifi_ssid": "test",
            "wifi_pass": "test",
            "admin_pass": "test",
            "vpn_enabled": False,
            "ospf_enabled": False,
            "bgp_enabled": False,
            "container_enabled": False,
            "pihole_enabled": False,
            "qos_type": "none"
        }

    def test_simple(self):
        ctx = self.base_ctx.copy()
        ctx['scenario_mode'] = 'simple'
        script = self.gen.generate(ctx)
        # Simple template is routeros_v7_base.j2
        # Just check it renders something valid
        self.assertIn("/interface bridge", script)

    def test_branch(self):
        ctx = self.base_ctx.copy()
        ctx['scenario_mode'] = 'branch'
        ctx['wan1_ip'] = "1.2.3.4/24"
        ctx['wan1_gateway'] = "1.2.3.1"
        ctx['wan2_interface'] = "lte1"
        ctx['vlan_ids'] = ["10", "20"]
        ctx['hq_wg_pubkey'] = "KEY123"

        script = self.gen.generate(ctx)
        self.assertIn("Scenario A", script)
        self.assertIn("vlan-filtering=yes", script)
        self.assertIn("vlan10", script)
        self.assertIn("KEY123", script)
        # Verify Dual-WAN Failover (Scenario 4)
        self.assertIn("check-gateway=ping", script)
        self.assertIn("gateway=8.8.8.8", script)

    def test_adblock(self):
        ctx = self.base_ctx.copy()
        ctx['scenario_mode'] = 'simple'
        ctx['adblock_enabled'] = True

        script = self.gen.generate(ctx)
        self.assertIn("/ip dns adlist add", script)
        self.assertIn("StevenBlack", script)

    def test_wisp(self):
        ctx = self.base_ctx.copy()
        ctx['scenario_mode'] = 'wisp'
        ctx['mgmt_ip'] = "10.0.0.100"
        ctx['ospf_area'] = "0.0.0.1"

        script = self.gen.generate(ctx)
        self.assertIn("Scenario C", script)
        self.assertIn("pppoe-server", script)
        self.assertIn("wisp-area", script)

    def test_voip(self):
        ctx = self.base_ctx.copy()
        ctx['voip_enabled'] = True
        script = self.gen.generate(ctx)
        self.assertIn("VoIP Prioritization", script)
        self.assertIn("packet-marks=voip_pkt", script)

    def test_hotspot(self):
        ctx = self.base_ctx.copy()
        ctx['hotspot_enabled'] = True
        script = self.gen.generate(ctx)
        self.assertIn("Hotspot Portal", script)
        self.assertIn("/ip hotspot profile add", script)

if __name__ == "__main__":
    unittest.main()
