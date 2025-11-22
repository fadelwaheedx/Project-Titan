import flet as ft
import threading
import http.server
import socketserver
import os
import sys

# Add src to path to find modules if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from discovery.mndp_scanner import MNDP_Scanner
from ui.wizard import Wizard
from logic.auditor import RouterAuditor
from ui.monitor import TrafficMonitor

# --- Local Assets Server (Bridging Python & WebView) ---
# This is required because WebViews cannot load local files with CORS enabled.
PORT = 8000

# Resolve ASSETS_DIR considering PyInstaller freeze
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    # sys._MEIPASS is the temp directory where PyInstaller extracts files
    ASSETS_DIR = os.path.join(sys._MEIPASS, "assets")
else:
    # Running as script
    ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ASSETS_DIR, **kwargs)

def start_asset_server():
    # Allow reuse address to prevent "Address already in use" errors during restarts
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Asset server running at http://localhost:{PORT}")
        httpd.serve_forever()

# Start server in background thread
server_thread = threading.Thread(target=start_asset_server, daemon=True)
server_thread.start()

# --- Main Application ---
def main(page: ft.Page):
    page.title = "Project Titan - MikroTik Commander"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    
    # Initialize Scanner
    scanner = MNDP_Scanner()
    
    # --- State ---
    router_ip = ft.TextField(label="Router IP", value="192.168.88.1", width=200)
    router_user = ft.TextField(label="User", value="admin", width=200)
    router_pass = ft.TextField(label="Password", password=True, can_reveal_password=True, width=200)
    
    # --- JavaScript Bridge (The Visualization Core) ---
    # This WebView loads the local HTML containing Cytoscape.js
    def handle_graph_message(e):
        """Handles messages from the Javascript graph (Click Events)."""
        clicked_ip = e.data
        print(f"Graph clicked IP: {clicked_ip}")
        
        # Auto-fill the IP field and notify user
        router_ip.value = clicked_ip
        
        # Trigger Audit Immediately as requested in Task 4.3
        # "When a node ... is clicked, trigger the run_compliance_scan ... and show the results"
        run_audit(None)

    topology_view = ft.WebView(
        url=f"http://localhost:{PORT}/index.html",
        expand=True,
        on_page_started=lambda _: print("Graph Loading..."),
        on_web_resource_error=lambda e: print("Web Error:", e.data),
        on_message=handle_graph_message,
    )

    def run_scan(e):
        page.snack_bar = ft.SnackBar(ft.Text("Scanning for Neighbors (MNDP)..."))
        page.snack_bar.open = True
        page.update()
        
        # Start Scan
        scanner.start_scan()
        
        # Give it a moment to find packets (since it's threaded)
        # In a real app we'd use a timer or stream events, but here we'll just invoke update shortly after
        # or we can just rely on the user clicking 'Scan' again or a 'Refresh' loop.
        # For this demo, we'll grab what we have immediately (which might be empty first click) 
        # and suggest re-clicking, or wait a tiny bit.
        import time
        time.sleep(1) 
        
        # Get data and inject into WebView
        json_data = scanner.get_neighbors_json()
        # print(f"Injecting Graph Data: {json_data}")
        
        safe_json_data = json_data.replace("'", "\\'")
        topology_view.evaluate_javascript(f"updateTopology('{safe_json_data}')")

    def run_audit(e):
        """Runs the compliance audit on the currently targeted IP."""
        target = router_ip.value
        user = router_user.value
        password = router_pass.value
        
        if not target:
            page.snack_bar = ft.SnackBar(ft.Text("Please enter a Router IP to audit."))
            page.snack_bar.open = True
            page.update()
            return

        page.snack_bar = ft.SnackBar(ft.Text(f"Auditing {target}..."))
        page.snack_bar.open = True
        page.update()
        
        def audit_task():
            auditor = RouterAuditor()
            report = auditor.run_compliance_scan(target, user, password)
            
            # Build Report UI
            items = []
            for check in report["checks"]:
                icon = ft.icons.CHECK_CIRCLE if check["status"] == "PASS" else ft.icons.WARNING
                color = ft.colors.GREEN if check["status"] == "PASS" else (ft.colors.ORANGE if check["status"] == "WARNING" else ft.colors.RED)
                items.append(
                    ft.ListTile(
                        leading=ft.Icon(icon, color=color),
                        title=ft.Text(check["name"]),
                        subtitle=ft.Text(f"{check['status']}: {check['details']}")
                    )
                )
            
            dlg = ft.AlertDialog(
                title=ft.Text(f"Audit Report: {target}"),
                content=ft.Column(items, height=300, scroll=ft.ScrollMode.AUTO),
                actions=[ft.TextButton("Close", on_click=lambda e: close_dlg())],
            )
            
            def close_dlg():
                page.dialog.open = False
                page.update()
                
            page.dialog = dlg
            dlg.open = True
            page.update()

        threading.Thread(target=audit_task, daemon=True).start()

    # --- Layout Management ---
    
    # Views
    scan_view_content = ft.Container(content=topology_view, expand=True)
    
    # Login / Control Panel for Scan View
    login_controls = ft.Column(
        [
            ft.Text("MikroTik Login", size=20, weight=ft.FontWeight.BOLD),
            router_ip,
            router_user,
            router_pass,
            ft.ElevatedButton("Scan Neighbors", icon=ft.icons.RADAR, on_click=run_scan),
            ft.ElevatedButton("Audit Device", icon=ft.icons.SECURITY, on_click=run_audit),
            ft.ElevatedButton("Start Setup (Wizard)", icon=ft.icons.SETTINGS, on_click=lambda e: switch_view(1)),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20
    )

    login_container = ft.Container(
        content=login_controls,
        padding=50,
        width=400,
        bgcolor=ft.colors.SURFACE_VARIANT,
        border_radius=10,
    )

    scan_layout = ft.Row(
        [
            login_container,
            ft.VerticalDivider(width=1),
            scan_view_content
        ],
        expand=True
    )
    
    wizard_view = Wizard(on_complete=lambda script: print("Wizard Complete"))
    monitor_view = TrafficMonitor(router_ip=router_ip.value, router_user=router_user.value, router_pass=router_pass.value)
    
    # Update monitor credentials when changed in login
    def update_monitor_creds(e):
        monitor_view.router_ip = router_ip.value
        monitor_view.router_user = router_user.value
        monitor_view.router_pass = router_pass.value
        # Restart poller if running is tricky, but UserControl did_mount handles restart on view switch.
        # We leave it to the user to switch tabs to refresh.

    router_ip.on_change = update_monitor_creds
    router_user.on_change = update_monitor_creds
    router_pass.on_change = update_monitor_creds

    # Container to hold the current view
    content_area = ft.Container(content=scan_layout, expand=True)

    def switch_view(index):
        sidebar.selected_index = index
        if index == 0:
            content_area.content = scan_layout
        elif index == 1:
            content_area.content = wizard_view
        elif index == 2:
            # Update creds just in case
            monitor_view.router_ip = router_ip.value
            monitor_view.router_user = router_user.value
            monitor_view.router_pass = router_pass.value
            content_area.content = monitor_view
        page.update()

    # Sidebar (Navigation)
    sidebar = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.icons.LAN, 
                selected_icon=ft.icons.LAN_OUTLINED, 
                label="Scan"
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.SETTINGS, 
                selected_icon=ft.icons.SETTINGS_OUTLINED, 
                label="Wizard"
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.MONITOR_HEART, 
                selected_icon=ft.icons.MONITOR_HEART_OUTLINED, 
                label="Monitor"
            ),
        ],
        on_change=lambda e: switch_view(e.control.selected_index),
    )

    # Main Layout Row
    page.add(
        ft.Row(
            [
                sidebar,
                ft.VerticalDivider(width=1),
                content_area
            ],
            expand=True,
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
