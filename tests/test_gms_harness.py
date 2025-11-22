import unittest
import time
import sys
import os
import random
import string
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from logic.generator import ConfigGenerator
from logic.auditor import RouterAuditor

class GrandMasterSimulation(unittest.TestCase):
    def setUp(self):
        self.gen = ConfigGenerator()
        self.base_ctx = {
            "lan_ip": "192.168.88.1",
            "role": "Test",
            "wan_type": "dhcp",
            "wifi_ssid": "test",
            "wifi_pass": "test"
        }

    def test_phase1_scale_generation(self):
        """
        Phase 1: Extreme Scale.
        Simulate 20,000 iterations in template generation (Abusing 'vlan_ids').
        """
        print("\n--- GMS Phase 1: Extreme Scale (Template Rendering) ---")

        # Abuse 'vlan_ids' to simulate massive loop
        # Scenario Branch iterates: {% for vlan in vlan_ids %}
        count = 20000
        ctx = self.base_ctx.copy()
        ctx.update({
            "scenario_mode": "branch",
            "wan1_ip": "1.1.1.1/24",
            "wan1_gateway": "1.1.1.1",
            "wan2_interface": "lte1",
            "hq_wg_pubkey": "KEY",
            "vlan_ids": [str(i) for i in range(count)]
        })

        start = time.time()
        try:
            script = self.gen.generate(ctx)
            duration = time.time() - start
            print(f"Generated {count} VLANs in {duration:.4f}s")
            self.assertTrue(len(script) > 0)

            # Verify integrity of last item
            self.assertIn(f"vlan-id={count-1}", script)

            # Check size
            size_kb = len(script) / 1024
            print(f"Script Size: {size_kb:.2f} KB")

        except Exception as e:
            self.fail(f"GMS Phase 1 Failed: {e}")

    @patch('paramiko.SSHClient')
    def test_phase1_auditor_resilience(self, mock_ssh_cls):
        """
        Phase 1: Auditor Resilience.
        Simulate Auditor running against a massive config.
        """
        print("\n--- GMS Phase 1: Auditor Resilience ---")
        mock_client = MagicMock()
        mock_ssh_cls.return_value = mock_client

        auditor = RouterAuditor()

        # The current Auditor uses "count-only" which is O(1) for the app (O(N) for router).
        # We simulate the router returning a valid count.

        # Mock exec_command to return "1" or "0"
        mock_client.exec_command.return_value = (None, MagicMock(read=lambda: b"1"), None)

        try:
            report = auditor.run_compliance_scan("1.1.1.1", "admin", "pass")
            self.assertTrue(report["passed"] is False) # Because we returned "1" for admin check (fail)
            print("Auditor handled mock response successfully.")
        except Exception as e:
            self.fail(f"Auditor crashed: {e}")

    def test_phase2_feature_gaps(self):
        """
        Phase 2: Advanced Feature Interdependency.
        Check if the Generator supports MPLS/VPLS/QoS Hierarchy.
        """
        print("\n--- GMS Phase 2: Feature Gap Analysis ---")

        # Attempt to inject QoS hierarchy via context
        ctx = self.base_ctx.copy()
        ctx.update({
            "scenario_mode": "simple",
            "qos_tree": {"parent": "root", "children": [{"name": "c1"}]} # Hypothetical input
        })

        script = self.gen.generate(ctx)

        if "queue tree" in script:
             print("Unexpected: Queue Tree found (Feature exists?)")
        else:
             print("Confirmed: Queue Tree feature missing in templates.")

    def test_phase3_injection(self):
        """
        Phase 3: Deep Configuration Integrity.
        Test for Script Injection via template variables.
        """
        print("\n--- GMS Phase 3: Injection Stress Test ---")

        # Inject RouterOS command into a text field
        malformed_payload = 'test" disabled=yes; /user add name="hacker"; #'

        ctx = self.base_ctx.copy()
        ctx.update({
            "scenario_mode": "simple",
            "wifi_ssid": malformed_payload
        })

        script = self.gen.generate(ctx)

        # In RouterOS, string values in quotes must be escaped.
        # If the template uses "{{ wifi_ssid }}", it renders literally.
        # Result: ssid="test" disabled=yes; /user add name="hacker"; #"

        if '/user add name="hacker"' in script:
             print("CRITICAL VULNERABILITY: Script Injection succeeded via 'wifi_ssid'")
             # This breaks the "Configuration Integrity" goal
        else:
             print("PASS: Injection prevented.")

if __name__ == "__main__":
    unittest.main()
