import unittest
from logic.hardware_validator import HardwareValidator

class TestHardwareValidator(unittest.TestCase):
    def setUp(self):
        self.validator = HardwareValidator()

    def test_bridge_crs3xx(self):
        # CRS3xx should support multiple bridges
        result = self.validator.validate_bridge_config("CRS326-24G-2S+", 2)
        self.assertTrue(result['valid'])
        self.assertIsNone(result['error'])

    def test_bridge_crs5xx(self):
        # CRS5xx should support multiple bridges
        result = self.validator.validate_bridge_config("CRS504-4XQ-IN", 2)
        self.assertTrue(result['valid'])
        self.assertIsNone(result['error'])

    def test_bridge_rb4011(self):
        # RB4011 does not support multi-bridge offloading
        result = self.validator.validate_bridge_config("RB4011iGS+5HacQ2HnD", 2)
        self.assertFalse(result['valid'])
        self.assertIn("PERFORMANCE WARNING", result['error'])
        self.assertIn("RB4011", result['error'])

    def test_bridge_single_rb4011(self):
        # Single bridge is fine on RB4011
        result = self.validator.validate_bridge_config("RB4011", 1)
        self.assertTrue(result['valid'])

    def test_tzsp_generation(self):
        cmd = self.validator.generate_tzsp_config("192.168.1.50", "ether1")
        self.assertIn("streaming-server=192.168.1.50", cmd)
        self.assertIn("filter-interface=ether1", cmd)
        self.assertIn("/tool sniffer", cmd)

    def test_safe_mode_wrapper(self):
        commands = ["/ip address add address=1.1.1.1/24 interface=ether1"]
        script = self.validator.wrap_in_safe_mode(commands)

        # Check for scheduler creation
        self.assertIn("/system scheduler add", script)
        self.assertIn("SAFE_MODE_ROLLBACK", script)
        self.assertIn("interval=4m", script)

        # Check for command execution
        self.assertIn("/ip address add", script)

        # Check for scheduler removal (success path)
        self.assertIn("/system scheduler remove", script)

        # Check for error handling
        self.assertIn(":do {", script)
        self.assertIn("on-error={", script)

if __name__ == '__main__':
    unittest.main()
