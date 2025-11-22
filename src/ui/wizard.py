import flet as ft
import secrets
import string
import threading
import os
from logic.generator import ConfigGenerator
from logic.deployer import Deployer

class Wizard(ft.UserControl):
    def __init__(self, on_complete=None):
        super().__init__()
        self.on_complete = on_complete
        self.current_step = 0
        self.config_data = {}
        
        # --- Deployment State ---
        self.deploy_status = ft.Text("")
        self.deploy_progress = ft.ProgressBar(visible=False)

        # --- Form Fields ---
        # Basic Tab Fields
        self.role_dropdown = ft.Dropdown(
            label="Router Role",
            options=[
                ft.dropdown.Option("Home Router"),
                ft.dropdown.Option("Small Office"),
                ft.dropdown.Option("Branch Gateway"),
            ],
            value="Home Router"
        )
        
        self.wan_type_dropdown = ft.Dropdown(
            label="WAN Connection Type",
            options=[
                ft.dropdown.Option("dhcp", "DHCP (Automatic)"),
                ft.dropdown.Option("static", "Static IP"),
                ft.dropdown.Option("pppoe", "PPPoE"),
            ],
            value="dhcp",
            on_change=self._on_wan_change
        )
        
        # WAN Details (conditionally shown)
        self.wan_ip = ft.TextField(label="WAN IP Address", visible=False)
        self.wan_subnet = ft.TextField(label="Subnet Mask (CIDR)", value="24", visible=False)
        self.wan_gateway = ft.TextField(label="Gateway", visible=False)
        self.pppoe_user = ft.TextField(label="PPPoE Username", visible=False)
        self.pppoe_pass = ft.TextField(label="PPPoE Password", password=True, visible=False)

        self.lan_ip = ft.TextField(label="LAN IP Address", value="192.168.88.1")
        self.wifi_ssid = ft.TextField(label="WiFi SSID")
        self.wifi_pass = ft.TextField(label="WiFi Password", password=True, can_reveal_password=True)
        self.admin_pass = ft.TextField(label="New Admin Password", password=True, can_reveal_password=True, 
                                       value=self._generate_password())
        self.vpn_chk = ft.Checkbox(label="Enable Remote Work VPN (WireGuard)")

        # Routing Tab Fields
        self.ospf_chk = ft.Checkbox(label="Enable OSPFv3 (Area 0.0.0.0)")
        self.bgp_chk = ft.Checkbox(label="Enable BGP Peering")
        self.bgp_asn = ft.TextField(label="BGP ASN", value="65000")

        # Services Tab Fields
        self.container_chk = ft.Checkbox(label="Install Container Support")
        self.pihole_chk = ft.Checkbox(label="Deploy PiHole/AdGuard (Container)")
        self.pihole_url = ft.TextField(label="Container Image URL", value="https://ghcr.io/adguardteam/adguardhome")

        # QoS Tab Fields
        self.qos_dropdown = ft.Dropdown(
            label="Traffic Shaping Strategy",
            options=[
                ft.dropdown.Option("none", "None"),
                ft.dropdown.Option("simple", "Simple Queues"),
                ft.dropdown.Option("cake", "CAKE / FQ_Codel"),
            ],
            value="none"
        )

    def _generate_password(self, length=12):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for i in range(length))

    def _on_wan_change(self, e):
        val = self.wan_type_dropdown.value
        self.wan_ip.visible = (val == "static")
        self.wan_subnet.visible = (val == "static")
        self.wan_gateway.visible = (val == "static")
        self.pppoe_user.visible = (val == "pppoe")
        self.pppoe_pass.visible = (val == "pppoe")
        self.update()

    def build(self):
        self.step_content = ft.Column()
        self.update_step_view()
        return self.step_content

    def update_step_view(self):
        self.step_content.controls.clear()
        
        if self.current_step == 0:
            # Use Tabs for Step 0 (Configuration)
            
            # Basic Content
            basic_content = ft.Column([
                self.role_dropdown,
                self.wan_type_dropdown,
                self.wan_ip, self.wan_subnet, self.wan_gateway,
                self.pppoe_user, self.pppoe_pass,
                self.lan_ip,
                self.wifi_ssid,
                self.wifi_pass,
                self.admin_pass,
                self.vpn_chk
            ], scroll=ft.ScrollMode.AUTO)

            # Routing Content
            routing_content = ft.Column([
                self.ospf_chk,
                self.bgp_chk,
                self.bgp_asn
            ])

            # Services Content
            services_content = ft.Column([
                self.container_chk,
                self.pihole_chk,
                self.pihole_url
            ])

            # QoS Content
            qos_content = ft.Column([
                self.qos_dropdown
            ])

            tabs = ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    ft.Tab(text="Basic", content=ft.Container(content=basic_content, padding=10)),
                    ft.Tab(text="Routing", content=ft.Container(content=routing_content, padding=10)),
                    ft.Tab(text="Services", content=ft.Container(content=services_content, padding=10)),
                    ft.Tab(text="QoS", content=ft.Container(content=qos_content, padding=10)),
                ],
                expand=1,
            )

            self.step_content.controls.extend([
                ft.Text("Titan Configuration Wizard", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(content=tabs, height=400), # Fixed height for tabs area
                ft.Divider(),
                ft.Row([
                    ft.ElevatedButton("Generate Config", on_click=self.finish_wizard)
                ], alignment=ft.MainAxisAlignment.END)
            ])
            
        elif self.current_step == 3:
            # Final Step: Review
            script_preview = ft.TextField(
                value=self.config_data.get("script", ""),
                multiline=True,
                min_lines=10,
                max_lines=20,
                read_only=True,
                text_style=ft.TextStyle(font_family="monospace")
            )
            
            self.deploy_btn = ft.ElevatedButton(
                "Deploy Configuration", 
                icon=ft.icons.ROCKET_LAUNCH, 
                on_click=self.deploy_handler
            )
            
            self.step_content.controls.extend([
                ft.Text("Configuration Ready!", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Review the generated script below:"),
                script_preview,
                self.deploy_status,
                self.deploy_progress,
                ft.Row([
                     ft.ElevatedButton("Edit Settings", on_click=lambda e: self.goto_step(0)),
                     self.deploy_btn
                ])
            ])
            
        self.update()

    def goto_step(self, step):
        self.current_step = step
        self.update_step_view()

    def next_step(self, e):
        self.current_step += 1
        self.update_step_view()

    def prev_step(self, e):
        self.current_step -= 1
        self.update_step_view()

    def finish_wizard(self, e):
        # Collect Data
        context = {
            "role": self.role_dropdown.value,
            "wan_type": self.wan_type_dropdown.value,
            "wan_ip": self.wan_ip.value,
            "wan_subnet": self.wan_subnet.value,
            "wan_gateway": self.wan_gateway.value,
            "pppoe_user": self.pppoe_user.value,
            "pppoe_pass": self.pppoe_pass.value,
            "lan_ip": self.lan_ip.value,
            "wifi_ssid": self.wifi_ssid.value,
            "wifi_pass": self.wifi_pass.value,
            # Basic
            "vpn_enabled": self.vpn_chk.value,
            "admin_user": "titan_admin",
            "admin_pass": self.admin_pass.value,
            # Routing
            "ospf_enabled": self.ospf_chk.value,
            "bgp_enabled": self.bgp_chk.value,
            "bgp_asn": self.bgp_asn.value,
            # Services
            "container_enabled": self.container_chk.value,
            "pihole_enabled": self.pihole_chk.value,
            "pihole_url": self.pihole_url.value,
            # QoS
            "qos_type": self.qos_dropdown.value,
            
            "dns_redirect": True, # Default to true for hardening
            
            # WireGuard Defaults for generation (would be dynamic in real app)
            "wg_peer_public_key": "ReplaceWithClientPubKey",
            "wg_peer_allowed_ips": "10.0.100.2/32",
            "wg_interface_ip": "10.0.100.1/24"
        }
        
        # Generate Script
        generator = ConfigGenerator()
        try:
            script = generator.generate(context)
            self.config_data["script"] = script
            self.current_step = 3
            self.update_step_view()
            if self.on_complete:
                self.on_complete(script)
        except Exception as ex:
            self.step_content.controls.append(ft.Text(f"Error: {ex}", color="red"))
            self.update()

    def deploy_handler(self, e):
        """Handles the deployment in a background thread."""
        self.deploy_progress.visible = True
        self.deploy_btn.disabled = True
        self.deploy_status.value = "Starting Deployment..."
        self.update()
        
        # Save script to a temporary file for upload
        script_path = os.path.join(os.getcwd(), "setup.rsc")
        with open(script_path, "w") as f:
            f.write(self.config_data.get("script", ""))

        # Thread wrapper
        def run_deploy():
            deployer = Deployer()
            
            # Callback to update UI from thread
            def update_status(msg):
                self.deploy_status.value = msg
                self.update()

            # For Wizard, we assume we are connecting to the default IP (192.168.88.1) 
            # or the current management IP. In a real app, this would be passed in.
            # Here we hardcode the 'current' connection details for the context of the task.
            current_ip = "192.168.88.1" 
            current_user = "admin"
            current_pass = "" # Default password is empty
            
            target_lan_ip = self.lan_ip.value
            
            # Check if heavy payload (Container enabled)
            heavy = self.container_chk.value
            
            success = deployer.deploy_configuration(
                ip=current_ip,
                user=current_user,
                password=current_pass,
                local_rsc_path=script_path,
                target_lan_ip=target_lan_ip,
                status_callback=update_status,
                heavy_payload=heavy
            )
            
            self.deploy_progress.visible = False
            self.deploy_btn.disabled = False
            
            if success:
                def close_dlg(e):
                    self.page.dialog.open = False
                    self.page.update()
                    
                # Check for Container Warning
                msg = f"Configuration successfully applied!\n\nRouter is now accessible at {target_lan_ip}."
                
                if heavy: # Heavy means containers enabled
                    msg += "\n\n⚠️ ACTION REQUIRED: Container Mode\n" \
                           "1. Power off router.\n" \
                           "2. Hold Reset button.\n" \
                           "3. Power on.\n" \
                           "4. Release after 5 minutes (or when prompted)."

                dlg = ft.AlertDialog(
                    title=ft.Text("Deployment Success"),
                    content=ft.Text(msg),
                    actions=[
                        ft.TextButton("OK", on_click=close_dlg),
                    ],
                    on_dismiss=close_dlg,
                )
                self.page.dialog = dlg
                dlg.open = True
                update_status("Deployment Complete.")
            else:
                update_status("Deployment Failed. Check logs.")
            
            self.page.update()
            
            # Clean up temp file
            if os.path.exists(script_path):
                os.remove(script_path)

        threading.Thread(target=run_deploy, daemon=True).start()
