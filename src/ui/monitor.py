import flet as ft
import threading
import time
from logic.telemetry import TrafficPoller

class TrafficMonitor(ft.Container):
    def __init__(self, router_ip, router_user, router_pass):
        super().__init__()
        self.padding = 20
        self.expand = True
        self.router_ip = router_ip
        self.router_user = router_user
        self.router_pass = router_pass
        self.poller = None
        self.data_points_rx = [ft.LineChartDataPoint(i, 0) for i in range(60)]
        self.data_points_tx = [ft.LineChartDataPoint(i, 0) for i in range(60)]
        self.running = False
        
        self.chart = ft.LineChart(
            data_series=[
                ft.LineChartData(
                    data_points=self.data_points_rx,
                    stroke_width=2,
                    color=ft.Colors.CYAN,
                    curved=True,
                    stroke_cap_round=True,
                ),
                ft.LineChartData(
                    data_points=self.data_points_tx,
                    stroke_width=2,
                    color=ft.Colors.PURPLE,
                    curved=True,
                    stroke_cap_round=True,
                ),
            ],
            border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE)),
            horizontal_grid_lines=ft.ChartGridLines(
                interval=1, color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE), width=1
            ),
            vertical_grid_lines=ft.ChartGridLines(
                interval=10, color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE), width=1
            ),
            left_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(
                        value=1, label=ft.Text("1 Mbps", size=10, weight=ft.FontWeight.BOLD)
                    ),
                    ft.ChartAxisLabel(
                        value=10, label=ft.Text("10 Mbps", size=10, weight=ft.FontWeight.BOLD)
                    ),
                    ft.ChartAxisLabel(
                        value=50, label=ft.Text("50 Mbps", size=10, weight=ft.FontWeight.BOLD)
                    ),
                ],
                labels_size=40,
            ),
            bottom_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(
                        value=0, label=ft.Text("60s", size=10, weight=ft.FontWeight.BOLD)
                    ),
                    ft.ChartAxisLabel(
                        value=59, label=ft.Text("Now", size=10, weight=ft.FontWeight.BOLD)
                    ),
                ],
                labels_size=32,
            ),
            tooltip_bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.SURFACE_CONTAINER_HIGHEST),
            min_y=0,
            max_y=None, # Auto-scale
            min_x=0,
            max_x=59,
            expand=True,
        )

        self.stat_text = ft.Text("Waiting for data...", size=20, weight=ft.FontWeight.BOLD)

        self.interface_dropdown = ft.Dropdown(
            label="Interface",
            options=[
                ft.dropdown.Option("ether1"),
                ft.dropdown.Option("LAN-Bridge"),
                ft.dropdown.Option("wlan1"),
            ],
            value="ether1",
            on_change=lambda e: self.poller.set_interface(self.interface_dropdown.value)
        )

        self.content = ft.Column([
            ft.Text("Live Traffic Monitor", size=24, weight=ft.FontWeight.BOLD),
            self.interface_dropdown,
            ft.Container(self.chart, height=300, border_radius=10, padding=10),
            self.stat_text,
            ft.Row([
                ft.Row([ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.CYAN), ft.Text("Download (RX)")]),
                ft.Row([ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.PURPLE), ft.Text("Upload (TX)")]),
            ], spacing=20)
        ])

    def did_mount(self):
        self.running = True
        self.poller = TrafficPoller(self.router_ip, self.router_user, self.router_pass)
        self.poller.start()
        self._start_ui_loop()

    def will_unmount(self):
        self.running = False
        if self.poller:
            self.poller.stop()

    def _start_ui_loop(self):
        def loop():
            while self.running:
                stats = self.poller.get_stats()
                self._update_chart(stats)
                time.sleep(1)
        threading.Thread(target=loop, daemon=True).start()

    def _update_chart(self, stats):
        # Shift data
        rx_val = stats["rx"] / 1000000.0 # Convert to Mbps
        tx_val = stats["tx"] / 1000000.0

        # Update data points: remove first, add new at end, re-index
        # Actually simpler to just rotate values and keep X fixed 0-59?
        # Or slide window. Let's slide values.

        current_rx = [p.y for p in self.data_points_rx]
        current_tx = [p.y for p in self.data_points_tx]

        current_rx.pop(0)
        current_rx.append(rx_val)
        current_tx.pop(0)
        current_tx.append(tx_val)

        for i in range(60):
            self.data_points_rx[i].y = current_rx[i]
            self.data_points_tx[i].y = current_tx[i]

        self.chart.update()
        self.stat_text.value = f"RX: {rx_val:.2f} Mbps | TX: {tx_val:.2f} Mbps"
        self.stat_text.update()
