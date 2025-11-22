import unittest
import sys
import os
import flet as ft

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ui.wizard import Wizard
from ui.monitor import TrafficMonitor

class TestUIIntegrity(unittest.TestCase):
    def test_wizard_structure(self):
        # Instantiate Wizard
        wizard = Wizard()

        # Verify Inheritance
        self.assertIsInstance(wizard, ft.Column)

        # Verify Controls are populated (init moved from build)
        self.assertTrue(len(wizard.controls) > 0, "Wizard should have controls in __init__")

        # Check for specific components to ensure logic ran
        has_dropdown = any(isinstance(c, ft.Dropdown) for c in wizard.controls)
        self.assertTrue(has_dropdown, "Wizard should contain a Dropdown")

        # Check for new fields
        self.assertTrue(hasattr(wizard, 'hotspot_chk'), "Wizard should have hotspot_chk")
        self.assertTrue(hasattr(wizard, 'voip_chk'), "Wizard should have voip_chk")

    def test_monitor_structure(self):
        # Instantiate TrafficMonitor
        # It requires args: router_ip, router_user, router_pass
        monitor = TrafficMonitor("1.1.1.1", "admin", "pass")

        # Verify Inheritance
        self.assertIsInstance(monitor, ft.Container)

        # Verify Content
        self.assertIsNotNone(monitor.content, "Monitor content should be set")
        self.assertIsInstance(monitor.content, ft.Column)

        # Check for chart (it's wrapped in a Container in the Column)
        col = monitor.content
        found_chart = False
        for c in col.controls:
             if isinstance(c, ft.LineChart):
                 found_chart = True
             elif isinstance(c, ft.Container) and isinstance(c.content, ft.LineChart):
                 found_chart = True

        self.assertTrue(found_chart, "Monitor should contain a LineChart")

if __name__ == "__main__":
    unittest.main()
