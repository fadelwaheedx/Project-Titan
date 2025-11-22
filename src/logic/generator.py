import os
import jinja2
import datetime
import ipaddress

class ConfigGenerator:
    def __init__(self, template_dir=None):
        if template_dir is None:
            # Resolve relative to this file: ../../assets/templates
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.template_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "assets", "templates"))
        else:
            self.template_dir = template_dir

        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=jinja2.select_autoescape()
        )
        
        # Add custom filters
        self.env.filters['ip_network_start'] = self._filter_network_start
        self.env.filters['ip_network_end'] = self._filter_network_end
        self.env.filters['ip_network_base'] = self._filter_network_base

    def _filter_network_start(self, ip_str):
        """Returns the start IP of a DHCP pool (e.g., x.x.x.10) from an interface IP."""
        # ip_str is expected to be just the IP, e.g. "192.168.88.1"
        # We assume /24 for LAN usually, but let's just grab the first 3 octets
        parts = ip_str.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.10"
        return ip_str

    def _filter_network_end(self, ip_str):
        """Returns the end IP of a DHCP pool (e.g., x.x.x.254)."""
        parts = ip_str.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.254"
        return ip_str

    def _filter_network_base(self, ip_str):
        """Returns the network address (e.g., 192.168.88.0) assuming /24."""
        parts = ip_str.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
        return ip_str

    def generate(self, context):
        """
        Generates the RouterOS configuration script.
        
        Args:
            context (dict): Dictionary containing configuration parameters.
            
        Returns:
            str: The rendered configuration script.
        """
        # Add default context variables if missing
        if 'generation_date' not in context:
            context['generation_date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        template = self.env.get_template("routeros_v7_base.j2")
        return template.render(context)

if __name__ == "__main__":
    # Quick test
    gen = ConfigGenerator()
    ctx = {
        "role": "Home Router",
        "admin_user": "admin_secure",
        "admin_pass": "SuperSecret123",
        "wan_type": "dhcp",
        "lan_ip": "192.168.88.1",
        "wifi_ssid": "Titan_WiFi",
        "wifi_pass": "WifiPassword123",
        "vpn_enabled": True,
        "wg_peer_public_key": "ABC12345...",
        "wg_peer_allowed_ips": "10.10.10.2/32",
        "wg_interface_ip": "10.10.10.1/24",
        "dns_redirect": True,
        "adblock_enabled": False
    }
    print(gen.generate(ctx))
